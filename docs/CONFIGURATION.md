# Configuration

All runtime configuration is via environment variables. Every variable is optional and falls back to the default shown below. Set them before starting `server.py` (or in your Docker/compose `environment:` block).

## Cookie cache

| Variable | Default | Description |
|---|---|---|
| `CF_COOKIE_TTL_MINUTES` | `29` | How long generated Cloudflare clearance cookies are cached before they're considered expired and regenerated. Cloudflare `cf_clearance` cookies are short-lived, so keep this under ~30 minutes. |

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
| `CF_MAX_CONCURRENT_BROWSERS` | `4` | Maximum number of stealth-browser contexts launched at the same time. Caps memory/CPU under load; extra requests queue. |
| `CF_MAX_SESSIONS` | `128` | Maximum number of cached `curl_cffi` mirror sessions (LRU, one per `hostname:proxy`). The least-recently-used session is closed and evicted past this limit. |

## Browser engine (CloakBrowser)

| Variable | Default | Description |
|---|---|---|
| `CLOAKBROWSER_AUTO_UPDATE` | `false` | Set to `false` by the app so it does not check PyPI for a newer Chromium build on every launch. The bundled CloakBrowser library also reads `CLOAKBROWSER_BINARY_PATH`, `CLOAKBROWSER_CACHE_DIR`, and `CLOAKBROWSER_DOWNLOAD_URL` — see the CloakBrowser docs. |

## Example

```bash
export CF_COOKIE_TTL_MINUTES=20
export CF_IP_CHECK_ENABLED=true
export CF_MAX_CONCURRENT_BROWSERS=8
python server.py
```
