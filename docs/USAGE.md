# Usage

Bypass Cloudflare protection via a local server: generate clearance cookies, fetch rendered HTML, or transparently mirror any HTTP request. For environment-variable configuration (cookie TTL, proxy IP-checking, concurrency, etc.) see [CONFIGURATION.md](CONFIGURATION.md).

## Installation

### Docker Compose
```bash
git clone https://github.com/sarperavci/CloudflareBypassForScraping.git
cd CloudflareBypassForScraping
docker compose pull && docker compose up -d
```

### Docker (direct)
```bash
docker run -p 8000:8000 ghcr.io/sarperavci/cloudflarebypassforscraping:latest
```

Images are published for `linux/amd64` and `linux/arm64`. Besides `latest`, every release `vX.Y.Z` is tagged `X.Y.Z`, `X.Y` and `X`, so you can pin a version (e.g. `:3.0.0` or `:3`).

### Manual
Requires the [Brave browser](https://brave.com/linux/).
```bash
pip install -r server_requirements.txt
python server.py --browsers 3
```

`server.py` accepts `--host`, `--port`, `--workers`, `--log-level`, `--browsers` (reused browsers per worker, default 3), `--headless`, `--enable-cache` (cookie caching is off by default) and `--auth-token`. The Docker image runs Brave headless; arguments pass through, e.g. `docker run -p 8000:8000 IMAGE --browsers 5`.

### Build from source
```bash
docker build -t cloudflare-bypass .
docker run -p 8000:8000 cloudflare-bypass
```

## Authentication (optional)

Off by default. Start the server with a token and every request must carry it:

```bash
python server.py --auth-token change-me            # or: docker run -e CF_AUTH_TOKEN=change-me ...
curl -H "x-auth-token: change-me" "http://localhost:8000/cookies?url=https://example.com"
```

Requests without the header, or with a wrong value, get `401`. The `x-auth-token` header is stripped before mirrored requests reach the target site.

## Turnstile token generation — `/turnstile`

Generates Cloudflare Turnstile clearance tokens on-demand for target websites without loading heavy page assets.

Instead of navigating the browser through the full target page (which may load heavy scripts, trackers, or images), navigation is intercepted at the CDP network layer to inject a minimal widget-only page bound to the target origin. The token is solved using the pooled Brave browsers (no new browser launched) and returned with the matching `user-agent`.

### GET request
```bash
curl "http://localhost:8000/turnstile?url=https://example.com/login&sitekey=0x4AAAAAA..."
```

### POST request
```bash
curl -X POST "http://localhost:8000/turnstile" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/login",
    "sitekey": "0x4AAAAAA...",
    "action": "login",
    "cdata": "custom-payload",
    "pagedata": "optional-page-data",
    "proxy": "http://user:pass@host:port"
  }'
```

### Response
```json
{
  "token": "0.csb.XXXX.DUMMY.TOKEN.XXXX...",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
  "elapsed_time": 1.45,
  "sitekey": "0x4AAAAAA...",
  "url": "https://example.com/login"
}
```

Supports:
- Managed, non-interactive, and invisible Turnstile widgets.
- Automatic clicking of interactive checkboxes located inside shadow roots and cross-origin iframes.
- Per-request proxies (`http://`, `https://`, `socks4://`, `socks5://` with authentication).
- Immediate browser reuse via disposable browser contexts.

## Raw bytes — `/fetch`

Downloads any resource (PDF, image, JSON, ...) through the browser after clearing the challenge, and returns the original bytes with the upstream status code and `Content-Type`.

```bash
curl -o paper.pdf "http://localhost:8000/fetch?url=https://example.com/files/paper.pdf"
```

The browser clears Cloudflare on the URL's origin, then requests the resource from inside the page, so cookies, TLS fingerprint and JS-set state all apply. Accepts `proxy` and `bypassCookieCache` like `/html`. Size is capped by `CF_FETCH_MAX_BYTES`. Sites that put their own (non-Cloudflare) JavaScript gate in front of a file may still return that gate page.

`/cookies` also accepts `bypassCookieCache=true` to ignore a still-valid cached cookie and solve again.

## Browser pool status

```bash
$ curl http://localhost:8000/browsers
{"total":3,"available":2,"busy":1,"restarting":0,
 "browsers":[{"index":0,"state":"busy","jobs":12,"pid":4211}, ...]}
```

Counts are per worker process when running with `--workers > 1`.

## Request mirroring (any HTTP method)

Request mirroring forwards any HTTP request through the bypass server, handling both clearance-cookie generation and SSL/TLS fingerprinting. Point your API base URL at the local server and add the `x-hostname` header with the target host.

```bash
# GET request
curl "http://localhost:8000/api/data" -H "x-hostname: example-site-protected-with-cf.com"

# POST request
curl -X POST "http://localhost:8000/api/submit" \
  -H "x-hostname: cf-protected-website.com" \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'
```

The first request generates and caches Cloudflare cookies; subsequent requests reuse them automatically.

### Control headers

- `x-hostname` — target hostname (required; a bare host like `example.com`, not a full URL)
- `x-proxy` — proxy URL (optional), e.g. `http://user:pass@host:port`
- `x-bypass-cache` — force fresh cookie generation (optional)

```bash
curl "http://localhost:8000/api/data" \
  -H "x-hostname: protected-site.com" \
  -H "x-proxy: http://user:pass@proxyserver:port" \
  -H "x-bypass-cache: true"
```

## Cookie extraction

`/cookies` returns Cloudflare clearance cookies for a URL without mirroring a request.

```bash
curl "http://localhost:8000/cookies?url=https://nopecha.com/demo/cloudflare"
```
```json
{
  "cookies": {
    "cf_clearance": "SJHuYhHrTZpXDUe8iMuzEUpJxocmOW8ougQVS0.aK5g-1723665177-1.0.1.1-5_NOoP19LQZw4TQ4BLwJmtrXBoX8JbKF5ZqsAOxRNOnW2rmDUwv4hQ7BztnsOfB9DQ06xR5hR_hsg3n8xteUCw"
  },
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
}
```

## HTML extraction

`/html` returns the full rendered HTML of a page after bypassing Cloudflare (raw HTML, not JSON).

```bash
curl "http://localhost:8000/html?url=https://nopecha.com/demo/cloudflare"
```

Response includes these headers:
- `x-cf-bypasser-cookies` — number of cookies generated
- `x-cf-bypasser-user-agent` — user agent used for the bypass
- `x-cf-bypasser-final-url` — final URL after redirects
- `x-processing-time-ms` — processing time

## Backward compatibility

Existing integrations continue to work unchanged:

```bash
curl "http://localhost:8000/cookies?url=https://example.com"
```
