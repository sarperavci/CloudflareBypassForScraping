import json
import re
import os
from urllib.parse import urlparse
import tempfile
import hashlib

from CloudflareBypasser import CloudflareBypasser
from DrissionPage import ChromiumPage, ChromiumOptions
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from typing import Dict
import argparse

from pyvirtualdisplay import Display
import uvicorn
import atexit

# Check if running in Docker mode
DOCKER_MODE = os.getenv("DOCKERMODE", "false").lower() == "true"

SERVER_PORT = int(os.getenv("SERVER_PORT", 8000))

# Chromium options arguments
arguments = [
    # "--remote-debugging-port=9222",  # Add this line for remote debugging
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
    #"-incognito" # You can add this line to open the browser in incognito mode by default 
]

browser_path = "/usr/bin/google-chrome"
app = FastAPI()


# Pydantic model for the response
class CookieResponse(BaseModel):
    cookies: Dict[str, str]
    user_agent: str



def create_proxy_extension(username : str, password : str, endpoint : str, port : str):
    temp_dir = tempfile.gettempdir()
    unique_proxy_id = hashlib.sha256(f"{username}:{password}:{endpoint}:{port}".encode()).hexdigest()
    directory_name = os.path.join(temp_dir, unique_proxy_id)
    
    if os.path.exists(directory_name):
        return directory_name
    
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Proxies",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """

    background_js = """
    var config = {
            mode: "fixed_servers",
            rules: {
              singleProxy: {
                scheme: "http",
                host: "%s",
                port: parseInt(%s)
              },
              bypassList: ["localhost"]
            }
          };

    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

    function callbackFn(details) {
        return {
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        };
    }

    chrome.webRequest.onAuthRequired.addListener(
                callbackFn,
                {urls: ["<all_urls>"]},
                ['blocking']
    );
    """ % (endpoint, port, username, password)

    if not os.path.exists(directory_name):
        os.makedirs(directory_name)

    manifest_path = os.path.join(directory_name, "manifest.json")
    background_path = os.path.join(directory_name, "background.js")

    with open(manifest_path, "w") as file:
        file.write(manifest_json)
    
    with open(background_path, "w") as file2:
        file2.write(background_js)
    
    return directory_name

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
def bypass_cloudflare(url: str, retries: int, log: bool, proxy: str = None) -> ChromiumPage:
    options = ChromiumOptions().auto_port()
    options.set_paths(browser_path=browser_path).headless(False)

    if DOCKER_MODE:
        options.set_argument("--auto-open-devtools-for-tabs", "true")
        #options.set_argument("--remote-debugging-port=9222")
        options.set_argument("--no-sandbox") # Necessary for Docker
        options.set_argument("--disable-gpu") # Optional, helps in some cases
    
    if proxy:
        try:
            parsed_proxy = urlparse(proxy)
            scheme = parsed_proxy.scheme.lower() if parsed_proxy.scheme else 'http'
            hostname = parsed_proxy.hostname
            port = parsed_proxy.port
            username = parsed_proxy.username
            password = parsed_proxy.password

            if not hostname or not port:
                 raise ValueError("Proxy hostname or port missing")

            if scheme in ['http', 'https']:
                 if username and password:
                      proxy_extension_path = create_proxy_extension(username, password, hostname, str(port))
                      options.add_extension(proxy_extension_path)
                 elif not username and not password:
                      options.set_proxy(f"{scheme}://{hostname}:{port}")
                 else:
                     raise ValueError("Proxy requires both username and password, or neither.")
            elif scheme.startswith('socks'):
                 print(f"Warning: SOCKS proxy ({proxy}) is not supported due to chromium limitations.")
                 raise NotImplementedError("SOCKS proxy is not supported")
            else:
                 print(f"Warning: Unsupported proxy scheme '{scheme}'. Ignoring proxy.")

        except ValueError as e:
            print(f"Error parsing proxy string '{proxy}': {e}. Proceeding without proxy.")
            raise HTTPException(status_code=400, detail=str(e))


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
async def get_cookies(url: str, retries: int = 5, proxy: str = None):
    if not is_safe_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL")
    try:
        driver = bypass_cloudflare(url, retries, log, proxy)
        cookies = {cookie.get("name", ""): cookie.get("value", " ") for cookie in driver.cookies()}
        user_agent = driver.user_agent
        driver.quit()
        return CookieResponse(cookies=cookies, user_agent=user_agent)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint to get HTML content and cookies
@app.get("/html")
async def get_html(url: str, retries: int = 5, proxy: str = None):
    if not is_safe_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL")
    try:
        driver = bypass_cloudflare(url, retries, log, proxy)
        html = driver.html
        cookies_json = {cookie.get("name", ""): cookie.get("value", " ") for cookie in driver.cookies()}
        response = Response(content=html, media_type="text/html")
        response.headers["cookies"] = json.dumps(cookies_json)
        response.headers["user_agent"] = driver.user_agent
        driver.quit()
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Main entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cloudflare bypass api")

    parser.add_argument("--nolog", action="store_true", help="Disable logging")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")

    args = parser.parse_args()
    display = None
    
    if args.headless or DOCKER_MODE:
        display = Display(visible=0, size=(1920, 1080))
        display.start()
        
        def cleanup_display():
            if display:
                display.stop()
        atexit.register(cleanup_display)
    
    if args.nolog:
        log = False
    else:
        log = True

    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT)