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

### Using Docker Compose
```bash
git clone https://github.com/sarperavci/CloudflareBypassForScraping.git
cd CloudflareBypassForScraping
docker compose pull && docker compose up -d
```

### Using Docker directly
```bash
# Pull and run the latest image
docker run -p 8000:8000 ghcr.io/sarperavci/cloudflarebypassforscraping:latest
```

## Manual Installation
```bash
pip install -r requirements.txt
python server.py
```

# Usage

## Request Mirroring (Any HTTP Method)

Request mirroring is a new technique that allows you to forward any HTTP request through the Cloudflare bypass server. That lets you to handle seamlessly both clearance cookie generation and SSL/TLS fingerprinting challenges.

Simply, change your API base URL to point to the local server and add the `x-hostname` header with the target hostname. You can add other headers or body as needed.

```bash
# GET request
curl "http://localhost:8000/api/data" -H "x-hostname: example-site-protected-with-cf.com"

# POST request  
curl -X POST "http://localhost:8000/api/submit" \
  -H "x-hostname: cf-protected-website.com" \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'
```

Initial request will generate and cache Cloudflare cookies, subsequent requests will use cached cookies automatically. 

### Miscellaneous Headers

- `x-hostname`: Target hostname (required)
- `x-proxy`: Proxy URL (optional) 
- `x-bypass-cache`: Force fresh cookies (optional)

These three headers let you control the bypassing behavior per request. You can set them as needed.

```bash
curl "http://localhost:8000/api/data" \
  -H "x-hostname: protected-site.com" \
  -H "x-proxy: http://user:pass@proxyserver:port" \
  -H "x-bypass-cache: true"
```

### Basic Cookie Extraction

The `/cookies` endpoint allows you to get Cloudflare cookies for a specific URL without mirroring a request. A random Firefox version on a random OS is used as the user agent.

```bash
$ curl "http://localhost:8000/cookies?url=https://nopecha.com/demo/cloudflare"
```
```json
{
  "cookies": {
    "cf_clearance": "SJHuYhHrTZpXDUe8iMuzEUpJxocmOW8ougQVS0.aK5g-1723665177-1.0.1.1-5_NOoP19LQZw4TQ4BLwJmtrXBoX8JbKF5ZqsAOxRNOnW2rmDUwv4hQ7BztnsOfB9DQ06xR5hR_hsg3n8xteUCw"
  },
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0"
}
```

### HTML Content Extraction

The `/html` endpoint returns the full HTML content of a page after bypassing Cloudflare protection. The HTML is returned directly (not as JSON).

```bash
$ curl "http://localhost:8000/html?url=https://nopecha.com/demo/cloudflare"
```

This returns the raw HTML content with additional headers containing bypass information:
- `x-cf-bypasser-cookies`: Number of cookies generated
- `x-cf-bypasser-user-agent`: User agent used for bypass
- `x-cf-bypasser-final-url`: Final URL after redirects
- `x-processing-time-ms`: Time taken to process the request


## Build from Source  
```bash
# Build the image
docker build -t cloudflare-bypass .

# Run the container
docker run -p 8000:8000 cloudflare-bypass
```

# Backward Compatibility

Existing integrations continue to work unchanged:

```bash
# Legacy endpoint still works
curl "http://localhost:8000/cookies?url=https://example.com"

# Old bypass server - I'm keeping it as alternative method
pip install -r old_server_requirements.txt
python old_server.py
```

# Example Projects

- [Calibre Web Automated Book Downloader](https://github.com/calibrain/calibre-web-automated-book-downloader)
- [Kick Unofficial API](https://github.com/sarperavci/kick-unofficial-api)

# Contributing

Contributions welcome! Submit PRs against the main codebase.
