import asyncio
import logging
import os
import traceback
from collections import OrderedDict
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse

from curl_cffi.requests import AsyncSession

from cf_bypasser.core.bypasser import CloakBypasser
from cf_bypasser.utils.config import BrowserConfig
from cf_bypasser.utils.misc import cache_key
from cf_bypasser.utils.constants import (
    MAX_SESSIONS,
    MIRROR_MAX_RETRIES,
    MIRROR_RETRY_BACKOFF_SECONDS,
    SESSION_TIMEOUT_SECONDS,
)


class RequestMirror:
    """Handles dynamic request mirroring with Cloudflare bypass."""

    def __init__(self, bypasser: Optional[CloakBypasser] = None):
        self.bypasser: CloakBypasser = bypasser or CloakBypasser()
        self.session_cache: "OrderedDict[str, AsyncSession]" = OrderedDict()  # LRU per host:proxy
        self.max_sessions: int = int(os.environ.get("CF_MAX_SESSIONS", str(MAX_SESSIONS)))

    def strip_mirror_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Remove x-hostname, x-proxy, and x-bypass-cache headers from request."""
        cleaned_headers = {}
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower not in ['x-hostname', 'x-proxy', 'x-bypass-cache']:
                cleaned_headers[key] = value
        return cleaned_headers

    def merge_cookies(self, incoming_cookies: str, cf_cookies: Dict[str, str]) -> str:
        """Merge incoming cookies with Cloudflare clearance cookies."""
        try:
            incoming_dict = {}
            if incoming_cookies:
                for cookie in incoming_cookies.split(';'):
                    cookie = cookie.strip()
                    if '=' in cookie:
                        name, value = cookie.split('=', 1)
                        incoming_dict[name.strip()] = value.strip()

            # CF cookies are authoritative for any name they carry; other client cookies pass through.
            merged_cookies = dict(incoming_dict)
            merged_cookies.update(cf_cookies)

            cookie_pairs = [f"{name}={value}" for name, value in merged_cookies.items()]
            return '; '.join(cookie_pairs)
        except Exception as e:
            logging.error(f"Error merging cookies: {e}")
            # Fallback to CF cookies only
            return '; '.join([f"{name}={value}" for name, value in cf_cookies.items()])

    def build_target_url(self, hostname: str, path: str, query_string: Optional[str] = None) -> str:
        if not hostname.startswith(('http://', 'https://')):
            hostname = f"https://{hostname}"

        parsed = urlparse(hostname)
        base = f"{parsed.scheme}://{parsed.netloc}"

        # Collapse network-path / leading slashes so the client path can't swap the host.
        safe_path = "/" + (path or "").lstrip("/")

        url = base + safe_path
        if query_string:
            url += f"?{query_string}"

        return url

    async def get_session(self, hostname: str, proxy: Optional[str] = None) -> AsyncSession:
        session_key = f"{hostname}:{proxy or 'no-proxy'}"

        if session_key in self.session_cache:
            self.session_cache.move_to_end(session_key)
            return self.session_cache[session_key]

        proxy_dict = None
        if proxy:
            proxy_dict = {"http": proxy, "https": proxy}

        session = AsyncSession(
            impersonate="chrome",  # match CloakBrowser's Chrome fingerprint
            proxies=proxy_dict,
            timeout=SESSION_TIMEOUT_SECONDS
        )
        self.session_cache[session_key] = session
        self.session_cache.move_to_end(session_key)

        while len(self.session_cache) > self.max_sessions:
            _, evicted = self.session_cache.popitem(last=False)
            try:
                await evicted.close()
            except Exception as e:
                logging.error(f"Error closing evicted session: {e}")

        return session

    def _prepare_request_headers(self, headers: Dict[str, str], cf_data: Dict[str, Any]) -> Dict[str, str]:
        """Strip mirror/host headers, force the CF user-agent, merge cookies, add Chrome headers."""
        clean_headers = self.strip_mirror_headers(headers)

        # Override User-Agent with the one used for CF bypass
        clean_headers['user-agent'] = cf_data['user_agent']
        clean_headers.pop("host", None)

        incoming_cookies = ''
        cookie_header_key = None
        for key in clean_headers:
            if key.lower() == 'cookie':
                incoming_cookies = clean_headers[key]
                cookie_header_key = key
                break

        merged_cookies = self.merge_cookies(incoming_cookies, cf_data['cookies'])

        if cookie_header_key:
            del clean_headers[cookie_header_key]
        clean_headers['Cookie'] = merged_cookies

        # Add Chrome-like headers for better impersonation
        browser_headers = BrowserConfig.get_chrome_headers()
        for key, value in browser_headers.items():
            if key.lower() not in [h.lower() for h in clean_headers.keys()]:
                clean_headers[key] = value

        return clean_headers

    def _rewrite_response_headers(self, response: Any) -> Dict[str, str]:
        """Neutralize Content-Encoding and fix Content-Length to match the decoded body."""
        final_headers = {}
        for k, v in dict(response.headers).items():
            k_lower = k.lower()
            if k_lower == "content-encoding":
                final_headers[k] = "identity"
            elif k_lower == "content-length":
                final_headers[k] = str(len(response.content))
            else:
                final_headers[k] = v
        return final_headers

    async def mirror_request(
        self,
        method: str,
        path: str,
        query_string: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        hostname: Optional[str] = None,
        proxy: Optional[str] = None,
        bypass_cache: bool = False,
        body: Optional[bytes] = None,
        max_retries: int = MIRROR_MAX_RETRIES
    ) -> Tuple[int, Dict[str, str], bytes]:
        """Mirror the request to the target hostname (parsed by the caller) with CF bypass."""

        if not hostname:
            raise ValueError("x-hostname header is required")

        for attempt in range(max_retries + 1):
            try:
                logging.info(f"Mirroring {method} request to {hostname}{path} (attempt {attempt + 1}/{max_retries + 1})")

                target_url = self.build_target_url(hostname, path, query_string)

                # If bypass_cache is True, invalidate existing cache first
                if bypass_cache:
                    parsed_hostname = urlparse(target_url).netloc
                    self.bypasser.cookie_cache.invalidate(cache_key(parsed_hostname, proxy))

                cf_data = await self.bypasser.get_or_generate_cookies(target_url, proxy)

                if not cf_data:
                    raise Exception("Failed to get Cloudflare clearance cookies")

                clean_headers = self._prepare_request_headers(headers, cf_data)

                session = await self.get_session(hostname, proxy)

                response = await session.request(
                    method=method,
                    url=target_url,
                    headers=clean_headers,
                    data=body,
                    allow_redirects=False  # Let the client handle redirects
                )

                status_code = response.status_code

                if status_code == 403 and attempt < max_retries:
                    logging.warning(f"Got 403 Forbidden from {hostname}, invalidating cache and retrying...")

                    parsed_hostname = urlparse(target_url).netloc
                    self.bypasser.cookie_cache.invalidate(cache_key(parsed_hostname, proxy))

                    await asyncio.sleep(MIRROR_RETRY_BACKOFF_SECONDS)
                    continue

                final_headers = self._rewrite_response_headers(response)

                logging.info(f"Request to {hostname} completed with status {status_code}")
                return status_code, final_headers, response.content

            except (KeyError, TypeError, ValueError):
                # Deterministic programming errors — retrying won't help.
                raise
            except Exception as e:
                if attempt < max_retries:
                    logging.warning(f"Request attempt {attempt + 1} failed: {e}, retrying...")
                    await asyncio.sleep(MIRROR_RETRY_BACKOFF_SECONDS)
                    continue
                else:
                    logging.error(f"Error mirroring request after {max_retries + 1} attempts: {e}")
                    logging.error(traceback.format_exc())
                    raise

    async def cleanup(self):
        """Clean up resources."""
        for session in self.session_cache.values():
            try:
                await session.close()
            except Exception as e:
                logging.error(f"Error closing session: {e}")
        self.session_cache.clear()

        if self.bypasser:
            await self.bypasser.cleanup()
