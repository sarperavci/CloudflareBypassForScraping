# Cloudflare Bypass for Scraping

> ⭐ **Thank you for 1,800+ stars!** Introducing **Version 2.0** with enhanced request mirroring, improved caching and better reliability for bypassing Cloudflare protection.

Bypass Cloudflare protection with ease. Supports cookie generation and request mirroring for any HTTP method. 

## Sponsors

### Scrape.do

<a href="https://scrape.do/?utm_source=github&utm_medium=cfbypass"><img src="https://github.com/user-attachments/assets/04c49095-715b-4751-adf4-ae38fbe16e77" /></a>

[Scrape.do](https://scrape.do/?utm_source=github&utm_medium=cfbypass) is the ultimate toolkit for collecting public data at scale. Unmatched speed, unbeatable prices, unblocked access.

One line of code. Instant data access

- 🔁 Automatic Proxy Rotation 
- 🤖 Bypass Anti-bot Solutions 
- ⛏️ Seamless Web Scraping

[Claim your free trial](https://scrape.do/?utm_source=github&utm_medium=cfbypass)

### BirdProxies

<a href="https://birdproxies.com/t/sarperavci"><img src="https://github.com/user-attachments/assets/cac81306-49ea-44ae-b2bc-c16622803a99" /></a>

[BirdProxies](https://birdproxies.com/t/sarperavci) — Hey, we built BirdProxies because proxies shouldn't be complicated or overpriced. Fast residential and ISP proxies in 195+ locations, fair pricing, and real support. Try our FlappyBird game on the landing page for free data!

- Discord: [https://discord.com/invite/birdproxies](https://discord.com/invite/birdproxies)

# 🚀 Quick Start

```bash
docker run -p 8000:8000 ghcr.io/sarperavci/cloudflarebypassforscraping:latest
```

Then point your scraper at the server and add an `x-hostname` header:

```bash
curl "http://localhost:8000/api/data" -H "x-hostname: cf-protected-website.com"
```

# How it works

Two ways to get past Cloudflare, both powered by a real stealth browser (a patched Chromium via CloakBrowser).

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
