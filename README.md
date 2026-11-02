# Cloudflare Bypass for Scraping

> ⭐ **Thank you for 2,500+ stars!** Introducing **Version 3.0**: a reusable pool of headless Brave browsers driven by DrissionPage, per-request proxies (HTTP, HTTPS, SOCKS) without restarting the browser, faster Turnstile solving, a `/fetch` endpoint for files, optional `x-auth-token` auth and a lighter Docker image.

Bypass Cloudflare protection with ease. Supports cookie generation, Turnstile token generation, and request mirroring for any HTTP method. 

## Sponsors

### Scrape.do

<a href="https://scrape.do/?utm_source=github&utm_medium=cfbypass"><img src="https://github.com/user-attachments/assets/04c49095-715b-4751-adf4-ae38fbe16e77" /></a>

[Scrape.do](https://scrape.do/?utm_source=github&utm_medium=cfbypass) is the ultimate toolkit for collecting public data at scale. Unmatched speed, unbeatable prices, unblocked access.

One line of code. Instant data access

- 🔁 Automatic Proxy Rotation 
- 🤖 Bypass Anti-bot Solutions 
- ⛏️ Seamless Web Scraping

[Claim your free trial](https://scrape.do/?utm_source=github&utm_medium=cfbypass)

---


# 🚀 Quick Start

```bash
docker run -p 8000:8000 ghcr.io/sarperavci/cloudflarebypassforscraping:latest
```

Then point your scraper at the server and add an `x-hostname` header:

```bash
curl "http://localhost:8000/api/data" -H "x-hostname: cf-protected-website.com"
```

# How it works

Two ways to get past Cloudflare, both powered by a pool of real Brave browsers driven by DrissionPage and reused across requests.

## 🍪 Cookie generation — `/cookies`

Ask the server for clearance cookies for a URL and use them however you like:

```bash
curl "http://localhost:8000/cookies?url=https://protected-site.com"
```

```json
{
  "cookies": {
    "cf_clearance": "SJHuYhHrTZpXDUe8iMuzEUpJxocmOW8ougQVS0.aK5g-1723665177-1.0.1.1-5_NOoP19LQ..."
  },
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
}
```

Route the bypass through a proxy with the `proxy` query param:

```bash
curl "http://localhost:8000/cookies?url=https://protected-site.com&proxy=http://user:pass@host:port"
```

It launches a stealth browser, navigates to the URL, and solves the Cloudflare
challenge — non-interactive challenges resolve on their own, and interactive
Turnstile checkboxes are located inside their shadow DOM and clicked natively.
Once cleared, it returns the `cf_clearance` cookie **and** the exact
`user-agent` that earned it — you must send both together or Cloudflare rejects
the cookie. The pair is cached, so repeat calls are instant.

Use this when you drive your own HTTP client and just need valid cookies.

## 🪞 Mirror mode — any path + `x-hostname`

Point your scraper's base URL at the server and add an `x-hostname` header; the
server transparently proxies the request to the real site with Cloudflare
already bypassed. Add `x-proxy` to route through your own proxy:

```bash
curl -X POST "http://localhost:8000/api/submit" \
  -H "x-hostname: protected-site.com" \
  -H "x-proxy: http://user:pass@host:port" \
  -H "Content-Type: application/json" \
  -d '{"key":"value"}'
```

It generates (or reuses cached) clearance cookies for the host, then **replays
your exact request** — method, path, query, headers, body — to the real site
using an HTTP client that mimics Chrome's TLS/JA3 fingerprint, with the
Cloudflare cookies merged in. You get the real response back unchanged. This
clears **both** obstacles at once: the JavaScript challenge and TLS
fingerprinting — with no browser needed on your side.

Use this when you want a drop-in proxy that "just works" for any HTTP method.

## 🛡️ Turnstile token generation — `/turnstile`

Generate Cloudflare Turnstile clearance tokens on-demand for target websites:

```bash
curl "http://localhost:8000/turnstile?url=https://example.com/login&sitekey=0x4AAAAAA..."
```

Or via `POST`:

```bash
curl -X POST "http://localhost:8000/turnstile" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/login",
    "sitekey": "0x4AAAAAA...",
    "action": "login",
    "proxy": "http://user:pass@host:port"
  }'
```

```json
{
  "token": "0.csb.XXXX.DUMMY.TOKEN.XXXX...",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
  "elapsed_time": 1.45,
  "sitekey": "0x4AAAAAA...",
  "url": "https://example.com/login"
}
```

Instead of loading heavy, bloated web pages, it intercepts navigation at the CDP network layer and injects a clean, widget-only page for the target domain into a runtime Brave browser. Interactive Turnstile checkboxes are clicked automatically inside shadow roots and iframes.

See **[docs/USAGE.md](docs/USAGE.md)** for control headers, the `/html`
endpoint, and more.

# Documentation

- **[Usage](docs/USAGE.md)** — installation, request mirroring, the `/cookies` and `/html` endpoints, control headers.
- **[Configuration](docs/CONFIGURATION.md)** — environment variables (cookie TTL, proxy exit-IP checking, concurrency limits) and defaults.

# Example Projects

- [Calibre Web Automated Book Downloader](https://github.com/calibrain/calibre-web-automated-book-downloader)
- [Kick Unofficial API](https://github.com/sarperavci/kick-unofficial-api)

# Contributing

Contributions welcome! Submit PRs against the main codebase.
