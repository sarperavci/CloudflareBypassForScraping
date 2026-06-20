import ipaddress
import socket
from typing import Optional
from urllib.parse import urlparse


def _ip_is_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """True if the IP is loopback/private/link-local/etc and must be rejected."""
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _parse_ip_literal(host: str) -> Optional[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Parse host as an IP literal (dotted, integer, hex, octal); None if not an IP."""
    h = host.strip("[]")
    try:
        return ipaddress.ip_address(h)
    except ValueError:
        pass
    # integer (2130706433), hex (0x7f000001), octal-ish dotted forms (0177.0.0.1)
    try:
        return ipaddress.ip_address(int(h, 0))
    except (ValueError, OverflowError):
        pass
    try:
        packed = socket.inet_aton(h)
        return ipaddress.ip_address(packed)
    except OSError:
        return None


def is_safe_url(url: str) -> bool:
    """Check if the URL is safe (not localhost/private/internal); fails closed."""
    try:
        parsed_url = urlparse(url)
        if parsed_url.scheme == "file":
            return False
        hostname = parsed_url.hostname
        if not hostname:
            return False

        ip_literal = _parse_ip_literal(hostname)
        if ip_literal is not None:
            return not _ip_is_blocked(ip_literal)

        infos = socket.getaddrinfo(hostname, None)
        if not infos:
            return False
        for info in infos:
            addr = info[4][0]
            try:
                ip = ipaddress.ip_address(addr)
            except ValueError:
                return False
            if _ip_is_blocked(ip):
                return False
        return True
    except Exception:
        return False
