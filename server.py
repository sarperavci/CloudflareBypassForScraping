import json

from CloudflareBypasser import CloudflareBypasser
from DrissionPage import ChromiumPage, ChromiumOptions
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

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


class CookieResponse(BaseModel):
    cookies: dict


def bypass_cloudlflare(url, retries):
    # Set up Chromium options
    options = ChromiumOptions()
    options.set_paths(browser_path=browser_path).headless(False)

    # Initialize the browser
    driver = ChromiumPage(addr_or_opts=options)
    try:
        # Bypass
        driver.get(url)
        cf_bypasser = CloudflareBypasser(driver, retries, True)
        cf_bypasser.bypass()
        return driver
    except Exception as e:
        driver.quit()
        raise e


@app.get("/cookies", response_model=CookieResponse)
async def get_cookies(url: str, retries: int = 5):
    try:
        driver = bypass_cloudlflare(url, retries)
        cookies = driver.cookies(as_dict=True)
        driver.quit()
        return CookieResponse(cookies=cookies)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/html")
async def get_cookies(url: str, retries: int = 5):
    try:
        driver = bypass_cloudlflare(url, retries)
        html = driver.html

        cookies_json = json.dumps(driver.cookies(as_dict=True))

        response = Response(content=html, media_type="text/html")
        response.headers['cookies'] = cookies_json
        driver.quit()
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
