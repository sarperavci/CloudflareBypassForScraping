import json
import re
from urllib.parse import urlparse
from typing import Dict

from CloudflareBypasser import CloudflareBypasser
from DrissionPage import ChromiumPage, ChromiumOptions
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
import argparse

# Define the global variable `log`
log = True  # Default value

# Chromium options arguments
arguments = [
    "-no-first-run",
    "-force-color-profile=srgb",
    "-metrics-recording-only",
    "-password-store=basic",
    "-use-mock-keychain",
    "-export-tagged-pdf",
    "-no-default-browser-check",
    "-disable-background-mode",
    "-enable-features=NetworkService,NetworkServiceInProcess,LoadCryptoTokenExtension,PermuteTLSExtensions",
    "-disable-features=FlashDeprecationWarning,EnablePasswordsAccountStorage",
    "-deny-permission-prompts",
    "-disable-gpu",
    "-accept-lang=en-US",
]
browser_path = "/usr/bin/google-chrome"
app = FastAPI()


# Pydantic model for the response
class CookieResponse(BaseModel):
    cookies: Dict[str, str]
    user_agent: str


# Function to check if the URL is safe
def is_safe_url(url: str) -> bool:
    parsed_url = urlparse(url)
    ip_pattern = re.compile(
        r"^(127\.0\.0\.1|localhost|0\.0\.0\.0|::1|10\.\d+\.\d+\.\d+|172\.1[6-9]\.\d+\.\d+|172\.2[0-9]\.\d+\.\d+|172\.3[0-1]\.\d+\.\d+|192\.168\.\d+\.\d+)$"
    )
    hostname = parsed_url.hostname
    if (hostname and ip_pattern.match(hostname)) or parsed_url.scheme == "file":
        return False
    return True


# Function to bypass Cloudflare protection
def bypass_cloudflare(url: str, retries: int, headless: bool) -> ChromiumPage:
    options = ChromiumOptions()
    options.set_argument("--auto-open-devtools-for-tabs", "true")
    options.set_argument("--remote-debugging-port=9222")
    if headless:
        options.set_argument("--headless")
    options.set_argument("--no-sandbox")  # Add no-sandbox for Docker environments
    options.set_paths(browser_path=browser_path)

    driver = ChromiumPage(addr_or_opts=options)
    try:
        driver.get(url)
        cf_bypasser = CloudflareBypasser(driver, retries, log)
        cf_bypasser.bypass()
        return driver
    except Exception as e:
        driver.quit()
        raise e


# Endpoint to get cookies
@app.get("/cookies", response_model=CookieResponse)
async def get_cookies(url: str, retries: int = 5):
    if not is_safe_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL")
    headless = True  # Default value, can be overridden by arguments
    try:
        driver = bypass_cloudflare(url, retries, headless)
        cookies = driver.cookies(as_dict=True)
        user_agent = driver.user_agent
        driver.quit()
        return CookieResponse(cookies=cookies, user_agent=user_agent)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint to get HTML content and cookies
@app.get("/html")
async def get_html(url: str, retries: int = 5):
    if not is_safe_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL")
    headless = True  # Default value, can be overridden by arguments
    try:
        driver = bypass_cloudflare(url, retries, headless)
        html = driver.html
        cookies_json = json.dumps(driver.cookies(as_dict=True))

        response = Response(content=html, media_type="text/html")
        response.headers["cookies"] = cookies_json
        response.headers["user_agent"] = driver.user_agent
        driver.quit()
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Main entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cloudflare bypass API")

    parser.add_argument("--nolog", action="store_true", help="Disable logging")
    parser.add_argument(
        "--headless",
        type=str,
        choices=["true", "false"],
        default="true",
        help="Run in headless mode",
    )

    args = parser.parse_args()
    log = not args.nolog
    headless = args.headless.lower() == "true"

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
