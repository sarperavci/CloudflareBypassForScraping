
# Cloudflare Bypass Script - Updated in 22.04.2024

**We love scraping, don't we?** But sometimes, we face Cloudflare protection. This script is designed to bypass the Cloudflare protection on websites, allowing you to interact with them programmatically. 

# Sponsors
### [Capsolver](https://capsolver.com/?utm_source=github&utm_medium=banner_github&utm_campaign=CloudflareBypassForScraping)

[![Capsolver](docs/capsolver.jpg)](https://capsolver.com/?utm_source=github&utm_medium=banner_github&utm_campaign=CloudflareBypassForScraping)

[Capsolver.com](https://capsolver.com/?utm_source=github&utm_medium=banner_github&utm_campaign=CloudflareBypassForScraping) is
an AI-powered service that provides automatic captcha solving capabilities. It supports a range of captcha types,
including reCAPTCHA, hCaptcha, and FunCaptcha, AWS Captcha, Geetest, image captcha among others. Capsolver offers both
Chrome and Firefox extensions for ease of use, API integration for developers, and various pricing packages to suit
different needs.


# How does this script work?

If you use Selenium, you may have noticed that it is not possible to bypass Cloudflare protection with it. Even you click the "I'm not a robot" button, you will still be stuck in the "Checking your browser before accessing" page.
This is because Cloudflare protection is able to detect the automation tools and block them, which puts the webdriver infinitely in the "Checking your browser before accessing" page.

As you realize, the script uses the DrissionPage, which is a controller for the browser itself. This way, the browser is not detected as a webdriver and the Cloudflare protection is bypassed.

# Demo
![](docs/demo.gif)


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