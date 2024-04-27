
# Cloudflare Bypass Script - Updated in 22.04.2024

**We love scraping, don't we?** But sometimes, we face Cloudflare protection. This script is designed to bypass the Cloudflare protection on websites, allowing you to interact with them programmatically. 

# Sponsors
### [Capsolver](https://capsolver.com/?utm_source=github&utm_medium=banner_github&utm_campaign=CloudflareBypassForScraping)

[![Capsolver](docs/capsolver.jpg)](https://capsolver.com/?utm_source=github&utm_medium=banner_github&utm_campaign=CloudflareBypassForScraping)

[Capsolver.com](https://www.capsolver.com/?utm_source=github&utm_medium=banner_github&utm_campaign=CloudflareBypassForScraping) is an AI-powered service that specializes in solving various types of captchas automatically. It supports captchas such as [reCAPTCHA V2](https://docs.capsolver.com/guide/captcha/ReCaptchaV2.html), [reCAPTCHA V3](https://docs.capsolver.com/guide/captcha/ReCaptchaV3.html), [hCaptcha](https://docs.capsolver.com/guide/captcha/HCaptcha.html), [FunCaptcha](https://docs.capsolver.com/guide/captcha/FunCaptcha.html), [DataDome](https://docs.capsolver.com/guide/captcha/DataDome.html), [AWS Captcha](https://docs.capsolver.com/guide/captcha/awsWaf.html), [Geetest](https://docs.capsolver.com/guide/captcha/Geetest.html), and Cloudflare [Captcha](https://docs.capsolver.com/guide/antibots/cloudflare_turnstile.html) / [Challenge 5s](https://docs.capsolver.com/guide/antibots/cloudflare_challenge.html), [Imperva / Incapsula](https://docs.capsolver.com/guide/antibots/imperva.html), among others.

For developers, Capsolver offers API integration options detailed in their [documentation](https://docs.capsolver.com/), facilitating the integration of captcha solving into applications. They also provide browser extensions for both [Chrome](https://chromewebstore.google.com/detail/captcha-solver-auto-captc/pgojnojmmhpofjgdmaebadhbocahppod) and [Firefox](https://addons.mozilla.org/es/firefox/addon/capsolver-captcha-solver/), making it easy to use their service directly within a browser. Different pricing packages are available to accommodate varying needs, ensuring flexibility for users.


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

Create a new instance of the `CloudflareBypass` class and call the `bypass` method when you need to bypass the Cloudflare protection.

```python
from CloudflareBypasser import CloudflareBypasser

driver = ChromiumPage()
driver.get('https://nopecha.com/demo/cloudflare')

cf_bypasser = CloudflareBypasser(driver)
cf_bypasser.bypass()
```

You can run the test script to see how it works:

```bash
python test.py
```

## Drissionpage
To find out more about DrissionPage, you can get more information from the following links:
- [Official Github](https://github.com/g1879/DrissionPage)
  
- [Documantation](https://drissionpage.cn/)

Be sure you use a translation tool if you don't speak Chinese.

## Star History

<a href="https://star-history.com/#sarperavci/CloudflareBypassForScraping&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=sarperavci/CloudflareBypassForScraping&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=sarperavci/CloudflareBypassForScraping&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=sarperavci/CloudflareBypassForScraping&type=Date" />
 </picture>
</a>