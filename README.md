# Cloudflare Turnstile Page & Captcha Bypass for Scraping

**We love scraping, don't we?** But sometimes, we face Cloudflare protection. This script is designed to bypass the Cloudflare protection on websites, allowing you to interact with them programmatically. 

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



# How does this script work?

If you use Selenium, you may have noticed that it is not possible to bypass Cloudflare protection with it. Even you click the "I'm not a robot" button, you will still be stuck in the "Checking your browser before accessing" page.
This is because Cloudflare protection is able to detect the automation tools and block them, which puts the webdriver infinitely in the "Checking your browser before accessing" page.

As you realize, the script uses the DrissionPage, which is a controller for the browser itself. This way, the browser is not detected as a webdriver and the Cloudflare protection is bypassed.


## Installation

You can install the required packages by running the following command:

```bash
pip install -r requirements.txt
```

## Demo
![](https://cdn.sarperavci.com/xWhiMOmD/vzJylR.gif)

## Usage

Create a new instance of the `CloudflareBypass` class and call the `bypass` method when you need to bypass the Cloudflare protection.

```python
from CloudflareBypasser import CloudflareBypasser
from DrissionPage import ChromiumPage

driver = ChromiumPage()
driver.get('https://nopecha.com/demo/cloudflare')

cf_bypasser = CloudflareBypasser(driver)
cf_bypasser.bypass()
```

You can run the test script to see how it works:

```bash
python test.py
```

# Introducing Server Mode

Recently, [@frederik-uni](https://github.com/frederik-uni) has introduced a new feature called "Server Mode". This feature allows you to bypass the Cloudflare protection remotely, either you can get the cookies or the HTML content of the website.

## Installation

You can install the required packages by running the following command:

```bash
pip install -r server_requirements.txt
```

## Usage

Start the server by running the following command:

```bash
python server.py
```

Two endpoints are available:

- `/cookies?url=<URL>&retries=<>&proxy=<>`: This endpoint returns the cookies of the website (including the Cloudflare cookies).
- `/html?url=<URL>&retries=<>&proxy=<>`: This endpoint returns the HTML content of the website.

Send a GET request to the desired endpoint with the URL of the website you want to bypass the Cloudflare protection.

```bash
sarp@IdeaPad:~/$ curl http://localhost:8000/cookies?url=https://nopecha.com/demo/cloudflare
{"cookies":{"cf_clearance":"SJHuYhHrTZpXDUe8iMuzEUpJxocmOW8ougQVS0.aK5g-1723665177-1.0.1.1-5_NOoP19LQZw4TQ4BLwJmtrXBoX8JbKF5ZqsAOxRNOnW2rmDUwv4hQ7BztnsOfB9DQ06xR5hR_hsg3n8xteUCw"},"user_agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}
```

## Docker


You can also run the server in a Docker container. Thanks to [@gandrunx](https://github.com/gandrunx) for Dockerizing the server.

First, build the Docker image:

```bash
docker build -t cloudflare-bypass .
```

Then, run the Docker container:

```bash
docker run -p 8000:8000 cloudflare-bypass
```

Alternatively, you can skip `docker build` step, and run the container using pre-build image:
```bash
docker run -p 8000:8000 ghcr.io/sarperavci/cloudflarebypassforscraping:latest
```

## Example Projects

Here are some example projects that utilize the CloudflareBypasser Server:

- [Calibre Web Automated Book Downloader](https://github.com/calibrain/calibre-web-automated-book-downloader) - A tool to download books from calibre web.
- [Kick Unofficial API](https://github.com/sarperavci/kick-unofficial-api) - A tool to interact with the Kick.com, download videos, send messages, etc.

## Star History

<a href="https://star-history.com/#sarperavci/CloudflareBypassForScraping&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=sarperavci/CloudflareBypassForScraping&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=sarperavci/CloudflareBypassForScraping&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=sarperavci/CloudflareBypassForScraping&type=Date" />
 </picture>
</a>
