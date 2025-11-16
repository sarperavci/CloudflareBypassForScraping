# Cloudflare Bypass for Scraping

Bypass Cloudflare protection with ease. Supports cookie generation and request mirroring for any HTTP method. 

## Sponsors

### Scrapeless

[![](https://github.com/user-attachments/assets/783ce396-fa8c-4e10-846e-86d0ba0d0144)](https://www.scrapeless.com/en/product/scraping-browser?utm_source=github&utm_campaign=sarperavci)

[**Scrapeless Browser**](https://www.scrapeless.com/en/product/scraping-browser?utm_source=github&utm_campaign=sarperavci) is a cloud-based, Chromium-powered headless browser cluster. It allows developers to run large-scale, low-cost concurrent browser instances and reliably handle complex interactions on protected pages. Ideal for AI infrastructure, web automation, data scraping, page rendering, automated testing, and other tasks that require a real browser environment.  
**Key Advantages of Scrapeless Browser:**

* **Built-in CAPTCHA solving:** Automatically bypasses Cloudflare Turnstile, reCAPTCHA, AWS WAF, DataDome, and other challenge systems.  
* **Undetectable browser environment:** Not based on the traditional WebDriver — avoids automation detection.  
* **Massive concurrency support:** Run 50–10,000+ browser instances simultaneously with no server constraints.  
* **Real-time debugging:** Live View and session recording for efficient troubleshooting.  
* **Native integration:** Compatible with Puppeteer, Playwright, Python, and Node.js — easy to integrate into your current workflows.  
* **70M+ residential IPs:** Global proxy network with automatic rotation and smart geolocation routing.

In terms of cost, Scrapeless browser usage is only 1/8 of Browserbase, significantly cutting overall expenses.  
It also offers a [**Scraping API**](https://www.scrapeless.com/en/product/scraping-api?utm_source=github&utm_campaign=sarperavci)**、[Deep SerpApi](https://www.scrapeless.com/en/product/deep-serp-api?utm_source=github&utm_campaign=sarperavci) and [Proxies](https://www.scrapeless.com/en/product/proxies?utm_source=github&utm_campaign=sarperavci) services**.  
👉 Learn more: [Scrapeless Browser](https://www.scrapeless.com/en/product/scraping-browser?utm_source=github&utm_campaign=sarperavci) | [Documentation](https://docs.scrapeless.com/en/scraping-browser/quickstart/introduction/?utm_source=github&utm_campaign=sarperavci)

### ThorData

[![](https://github.com/user-attachments/assets/1aa1a5a0-d5bc-44bd-b446-9990bc898242)](https://www.thordata.com/?ls=github&lk=scraping)

[**ThorData Web Scraper**](https://www.thordata.com/products/web-scraper/?ls=github&lk=scraping) provides unblockable proxy infrastructure and scraping solutions for reliable, real-time web data extraction at scale. Perfect for AI training data collection, web automation, and large-scale scraping operations that require high performance and stability.  
**Key Advantages of ThorData:**

* **Massive proxy network:** Access to 60M+ ethically sourced residential, mobile, ISP, and datacenter IPs across 190+ countries.  
* **Enterprise-grade reliability:** 99.9% uptime with ultra-low latency (<0.5s response time) for uninterrupted data collection.  
* **Flexible proxy types:** Choose from residential, mobile (4G/5G), static ISP, or datacenter proxies based on your needs.  
* **Cost-effective pricing:** Starting from $1.80/GB for residential proxies with no traffic expiration and pay-as-you-go model.  
* **Advanced targeting:** City-level geolocation targeting with automatic IP rotation and unlimited bandwidth options.  
* **Ready-to-use APIs:** 120+ scraper APIs and comprehensive datasets purpose-built for AI and data science workflows.

ThorData is SOC2, GDPR, and CCPA compliant, trusted by 4,000+ enterprises for secure web data extraction.  
👉 Learn more: [ThorData Web Scraper](https://www.thordata.com/products/web-scraper/?ls=github&lk=scraping) | [Get Started](https://www.thordata.com/?ls=github&lk=scraping)  



# 🚀 Quick Start

## Docker (Recommended)

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
  -H "x-hostname: api.example.com" \
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