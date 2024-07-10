from CloudflareBypasser import CloudflareBypasser
from DrissionPage import ChromiumPage, ChromiumOptions
import time

if __name__ == '__main__':
    # Chromium Browser Path
    browser_path = "/usr/bin/google-chrome"

    # Windows Example
    #browser_path = r"C:/Program Files/Google/Chrome/Application/chrome.exe"

    options = ChromiumOptions()
    options.set_paths(browser_path=browser_path)

    # Some arguments to make the browser better for automation and less detectable.
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

    for argument in arguments:
        options.set_argument(argument)

    driver = ChromiumPage(addr_or_opts=options)

    driver.get('https://nopecha.com/demo/cloudflare')

    # Where the bypass starts
    cf_bypasser = CloudflareBypasser(driver)
    cf_bypasser.bypass()

    print("Enjoy the content!")

    #print(driver.html) # You can extract the content of the page.
    print("Title of the page: ", driver.title)

    time.sleep(5)
    driver.quit()
