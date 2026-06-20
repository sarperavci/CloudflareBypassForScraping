import os

APP_VERSION = "2.0.0"
DEFAULT_CACHE_FILE = "cf_cookie_cache.json"
COOKIE_TTL_MINUTES = int(os.environ.get("CF_COOKIE_TTL_MINUTES", "29"))
PROXY_SCHEMES = ("http://", "https://", "socks4://", "socks5://")

# Optional exit-IP check: re-verify the proxy's exit IP on a cache hit and invalidate
# if it rotated (residential proxies can change IP under us). Disabled by default.
def _env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes", "on")

IP_CHECK_ENABLED = _env_bool("CF_IP_CHECK_ENABLED", False)
IP_CHECK_URL = os.environ.get("CF_IP_CHECK_URL", "https://api.ipify.org")
IP_CHECK_TIMEOUT_SECONDS = int(os.environ.get("CF_IP_CHECK_TIMEOUT", "10"))
CF_COOKIE_PREFIXES = ("cf_", "__cf")
CF_PRIORITY_COOKIES = ("cf_clearance", "__cf_bm", "__cfruid")
DEFAULT_TIMEOUT_MS = 30000
CHALLENGE_SETTLE_SECONDS = 5
RETRY_POLL_SECONDS = 3
CONTEXT_CLOSE_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RETRIES = 5
MAX_CONCURRENT_BROWSERS = int(os.environ.get("CF_MAX_CONCURRENT_BROWSERS", "4"))
SESSION_TIMEOUT_SECONDS = 30
MIRROR_MAX_RETRIES = 2
MIRROR_RETRY_BACKOFF_SECONDS = 0.5
MAX_SESSIONS = int(os.environ.get("CF_MAX_SESSIONS", "128"))
CHROME_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0',
}
