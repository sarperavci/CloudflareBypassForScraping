import os

APP_VERSION = "3.0.0"
DEFAULT_CACHE_FILE = "cf_cookie_cache.json"
CACHE_ENABLED = os.environ.get("CF_CACHE_ENABLED", "false").lower() in ("1", "true", "yes", "on")  # off by default
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
CHALLENGE_POLL_SECONDS = 0.25
CHALLENGE_TIMEOUT_SECONDS = float(os.environ.get("CF_CHALLENGE_TIMEOUT", "30"))
TURNSTILE_TIMEOUT_SECONDS = float(os.environ.get("CF_TURNSTILE_TIMEOUT", "30"))
TURNSTILE_POLL_SECONDS = float(os.environ.get("CF_TURNSTILE_POLL", "0.2"))
CLICK_COOLDOWN_SECONDS = 3  # let the widget react before clicking again

# /html DOM-stability poll: sample page.content() until its size stops changing,
# so JS-rendered pages return a deterministic snapshot instead of a mid-render one.
HTML_SETTLE_POLL_SECONDS = float(os.environ.get("CF_HTML_SETTLE_POLL", "0.5"))
HTML_SETTLE_STABLE_ROUNDS = int(os.environ.get("CF_HTML_SETTLE_STABLE_ROUNDS", "2"))
HTML_SETTLE_MAX_SECONDS = float(os.environ.get("CF_HTML_SETTLE_MAX", "10"))
CONTEXT_CLOSE_TIMEOUT_SECONDS = 30
BROWSER_COUNT = int(os.environ.get("CF_BROWSERS", "3"))
HEADLESS = _env_bool("CF_HEADLESS", False)
BROWSER_PATH = os.environ.get("CF_BROWSER_PATH") or None  # Brave; auto-detected when unset
BROWSER_NO_SANDBOX = _env_bool("CF_BROWSER_NO_SANDBOX", False)
# Brave's own telemetry/update hosts (P3A, variations, updater); always blocked
BRAVE_DOMAINS = ("brave.com", "bravesoftware.com", "brave.software")
JOB_TIMEOUT_SECONDS = float(os.environ.get("CF_JOB_TIMEOUT", "120"))  # > sum of the inner timeouts
BROWSER_MAX_JOBS = int(os.environ.get("CF_BROWSER_MAX_JOBS", "200"))
FETCH_MAX_BYTES = int(os.environ.get("CF_FETCH_MAX_BYTES", str(50 * 1024 * 1024)))
SESSION_TIMEOUT_SECONDS = 30
MIRROR_MAX_RETRIES = int(os.environ.get("CF_MIRROR_MAX_RETRIES", "2"))
MIRROR_RETRY_BACKOFF_SECONDS = float(os.environ.get("CF_MIRROR_RETRY_DELAY", "0.5"))
MAX_SESSIONS = int(os.environ.get("CF_MAX_SESSIONS", "128"))
LOCALE = os.environ.get("CF_LOCALE", "en-US")


def accept_language(locale: str) -> str:
    return f"{locale},{locale.split('-')[0]};q=0.9" if "-" in locale else locale


CHROME_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': accept_language(LOCALE),
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0',
}
