
# Cloudflare Bypass Script - Updated in 14.04.2024

![](https://github.com/sarperavci/CloudflareBypassForScraping/blob/main/example.gif)

**We love scraping, don't we?** But sometimes, we face Cloudflare protection. This script is designed to bypass the Cloudflare protection on websites, allowing you to interact with them programmatically. It uses the [DrissionPage](https://github.com/g1879/DrissionPage) as a controller to interact with the browser and bypass the Cloudflare protection. The script is designed to work with the Chromium browser but it can be easily modified to work with other browsers as well.

# How does this script work?

If you use Selenium, you may have noticed that it is not possible to bypass Cloudflare protection with it. Even you click the "I'm not a robot" button, you will still be stuck in the "Checking your browser before accessing" page.
This is because Cloudflare protection is able to detect the automation tools and block them, which puts the webdriver infinitely in the "Checking your browser before accessing" page.

As you realize, the script uses the DrissionPage, which is a controller for the browser itself. This way, the browser is not detected as a webdriver and the Cloudflare protection is bypassed.

# What is this not?

This script is not related to bring a solution to bypass if your IP is blocked by Cloudflare. If you are blocked by Cloudflare, you need a clean IP to access the website. This script is designed to bypass the Cloudflare protection, not to bypass the IP block.

## Installation

Only dependency is DrissionPage, you can install it via pip:

```bash
pip install DrissionPage
```

# Usage

Run the script with the following command:

```bash
python3 cloudflare_bypass.py
```

The script will open a browser window and navigate to the website you want to scrape. For demo, this script navigates a website that has Cloudflare protection. You can change the website URL in the script to navigate to the website you want to scrape.

After the Cloudflare protection is bypassed, you can interact with the website programmatically.

## Drissionpage
To find out more about DrissionPage, you can get more information from the following links:
- [Official Github](https://github.com/g1879/DrissionPage)
  
- [Documantation](https://drissionpage.cn/)

Be sure you use a translation tool if you don't speak Chinese.