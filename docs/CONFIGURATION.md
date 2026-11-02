# Configuration

All runtime configuration is via environment variables. Every variable is optional and falls back to the default shown below. Set them before starting `server.py` (or in your Docker/compose `environment:` block).

## Authentication

| Variable | Default | Description |
|---|---|---|
| `CF_AUTH_TOKEN` | unset (off) | When set, every request (all endpoints, mirroring, `/browsers`, the API docs) must send `x-auth-token: <value>` or gets `401`. Same as `server.py --auth-token`. The header is never forwarded to mirrored sites. Leave unset to keep the server open, e.g. on a private network. |

## Caching (off by default)

By default nothing is cached: every request solves the challenge in a fresh browser context, nothing is written to disk, and request mirroring uses a fresh HTTP session per request, so no cookies carry over between requests or clients. Turn caching on to reuse clearance cookies (much faster for repeated requests to the same site, especially mirroring).

| Variable | Default | Description |
|---|---|---|
| `CF_CACHE_ENABLED` | `false` | Cache clearance cookies (in memory and in `cf_cookie_cache.json`) and reuse mirror sessions. Same as `server.py --enable-cache`. `/cache/stats` and `/cache/clear` work either way. |
| `CF_COOKIE_TTL_MINUTES` | `29` | How long generated Cloudflare clearance cookies are cached before they're considered expired and regenerated. Only used when caching is enabled. Cloudflare `cf_clearance` cookies are short-lived, so keep this under ~30 minutes. |

## Proxy exit-IP check

A rotating residential proxy can change its exit IP unexpectedly, which invalidates the `cf_clearance` cookie bound to the old IP. When enabled, the bypasser checks the proxy's current exit IP on each cache hit and, if it changed since the cookies were generated, invalidates the cache immediately and regenerates. Disabled by default (adds one HTTP request per cache hit when on).

| Variable | Default | Description |
|---|---|---|
| `CF_IP_CHECK_ENABLED` | `false` | Enable the exit-IP check. Accepts `1`/`true`/`yes`/`on`. |
| `CF_IP_CHECK_URL` | `https://api.ipify.org` | Endpoint that echoes the caller's IP as plain text. The request is made through the active proxy. |
| `CF_IP_CHECK_TIMEOUT` | `10` | Timeout in seconds for the exit-IP request. |

## Concurrency & resources

| Variable | Default | Description |
|---|---|---|
| `CF_BROWSERS` | `3` | Number of Brave processes kept running and reused (per worker). Each request borrows one; extra requests queue. Same as `server.py --browsers N`. |
| `CF_BROWSER_MAX_JOBS` | `200` | A browser is restarted after serving this many requests, to keep memory in check. |
| `CF_JOB_TIMEOUT` | `120` | Seconds one request may hold a browser. On timeout the browser is killed and relaunched. |
| `CF_CHALLENGE_TIMEOUT` | `30` | Seconds to keep polling/clicking the Turnstile checkbox before giving up. |
| `CF_TURNSTILE_TIMEOUT` | `30` | Seconds to wait for Turnstile token generation before timing out. |
| `CF_TURNSTILE_POLL` | `0.2` | Interval in seconds between status checks when solving Turnstile. |
| `CF_MIRROR_MAX_RETRIES` | `2` | Extra attempts for a mirrored request after a 403 or network error. |
| `CF_MIRROR_RETRY_DELAY` | `0.5` | Seconds to wait between mirror retries; raise it to avoid hammering a site. |
| `CF_MAX_SESSIONS` | `128` | Maximum number of cached `curl_cffi` mirror sessions (LRU, one per `hostname:proxy`). The least-recently-used session is closed and evicted past this limit. |

## Browser (Brave via DrissionPage)

| Variable | Default | Description |
|---|---|---|
| `CF_BROWSER_PATH` | auto-detect | Path to the Brave executable. When unset, the standard macOS/Linux install locations are tried; startup fails if Brave isn't found. |
| `CF_HEADLESS` | `false` (`true` in Docker) | Run Brave headless. Same as `server.py --headless`. |
| `CF_LOCALE` | `en-US` | Browser language (`--lang`/`Accept-Language`) and the `Accept-Language` sent by request mirroring. Match it to your proxy's region. |
| `CF_HTML_SETTLE_POLL` | `0.5` | Seconds between HTML snapshots while `/html` waits for the page to stop changing. |
| `CF_HTML_SETTLE_STABLE_ROUNDS` | `2` | Identical snapshots in a row needed before `/html` returns. |
| `CF_HTML_SETTLE_MAX` | `10` | Longest `/html` waits for the page to settle, in seconds. |
| `CF_FETCH_MAX_BYTES` | `52428800` | Largest response `/fetch` returns (50 MB). |
| `CF_BROWSER_NO_SANDBOX` | `false` (`true` in Docker) | Pass `--no-sandbox`; needed inside containers under Docker's default seccomp profile. Applied automatically when running as root. The browser loads URLs your clients choose, so treat the container as untrusted: it runs as a non-root user and holds no secrets, and you can re-enable the sandbox by running with a seccomp profile that allows user namespaces and setting this to `false`. |
| `PORT` | `8000` | Port the server listens on (same as `--port`); the Docker healthcheck follows it. |

Brave's own telemetry/update hosts (`brave.com`, `bravesoftware.com`, `brave.software` and their subdomains) are always blocked: unresolvable in the browser and refused by the proxy relay. Brave's telemetry can't be disabled any other way. As a consequence, Brave's own websites can't be scraped.

## Proxies

Every request runs in its own disposable browser context, so each request can use a different proxy (`proxy=` query param or `x-proxy` header) without restarting the browser. Plain `http://host:port` proxies are handed to the browser directly; proxies with credentials (`http://user:pass@host:port`) and SOCKS proxies go through a small relay on `127.0.0.1`, because the browser can't authenticate per-context proxies itself. A request with an invalid or unreachable proxy fails; it never falls back to a direct connection.

## Example

```bash
export CF_COOKIE_TTL_MINUTES=20
export CF_IP_CHECK_ENABLED=true
python server.py --browsers 8
```
