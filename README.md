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

### RapidProxy

<a href="https://www.rapidproxy.io/?ref=sarperavci"><img src="https://github.com/user-attachments/assets/6d3819b8-7065-4bd4-bda7-b06e0fe04477" /></a>

[RapidProxy](https://www.rapidproxy.io/?ref=sarperavci) – Power Your Data with Premium Proxies

🎁 Try proxies [for free](https://www.rapidproxy.io/?ref=sarperavci) + Use code **RAPID10** for 10% OFF

- 90M+ IPs in 200+ countries & regions
- No expiration on traffic — use anytime, no pressure
- Unlimited concurrency for maximum performance
- Starting from just $0.65/GB — built for scale
- City-level targeting for precise geo access
- Flexible session control tailored to your needs
- Enterprise-grade speed & reliability
- Built for large-scale automation

**💡 Built for Growth** — Whether you're scaling scraping operations, running automation, or accessing global content, RapidProxy delivers the speed, stability, and flexibility you need to grow without limits.

👉 [Start your free trial today](https://www.rapidproxy.io/?ref=sarperavci)

---


# 🚀 Quick Start

```bash
docker run -p 8000:8000 ghcr.io/sarperavci/cloudflarebypassforscraping:latest
```

Then point your scraper at the server and add an `x-hostname` header:

```bash
curl "http://localhost:8000/api/data" -H "x-hostname: cf-protected-website.com"
```

# Documentation

- **[Usage](docs/USAGE.md)** — installation, request mirroring, the `/cookies` and `/html` endpoints, control headers.
- **[Configuration](docs/CONFIGURATION.md)** — environment variables (cookie TTL, proxy exit-IP checking, concurrency limits) and defaults.

# Example Projects

- [Calibre Web Automated Book Downloader](https://github.com/calibrain/calibre-web-automated-book-downloader)
- [Kick Unofficial API](https://github.com/sarperavci/kick-unofficial-api)

# Contributing

Contributions welcome! Submit PRs against the main codebase.
