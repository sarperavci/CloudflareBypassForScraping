import time
from DrissionPage import ChromiumPage, ChromiumOptions

# This code is written for readibility and simplicity. It is not optimized for performance.
# You can optimize the code by removing the unnecessary sleeps and checks.


def clickCycle(driver: ChromiumPage):
    #reach the captcha button and click it
    # if iframe does not exist, it means the page is already bypassed.
    if driver.wait.ele_displayed('xpath://div/iframe',timeout=1.5):
        time.sleep(1.5)
        driver('xpath://div/iframe').ele(".ctp-checkbox-label", timeout=2.5).click()
        # The location of the button may vary time to time. I sometimes check the button's location and update the code.
        return True
    return False

def isBypassed(driver: ChromiumPage):
    title = driver.s_ele('xpath://h3').text.lower()
    # If the title does not contain "just a moment", it means the page is bypassed.
    # This is a simple check, you can implement more complex checks.
    return "just a moment" not in title
 
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
    ]

    for argument in arguments:
        options.set_argument(argument)

    driver = ChromiumPage(addr_driver_opts=options)

    driver.get('https://nopecha.com/demo/cloudflare')

    # Where the bypass starts
    while True:
        time.sleep(2)
        if isBypassed(driver):
            print("Bypassed!")
            break

        # A click may be enough to bypass the captcha, if your IP is clean.
        # I haven't seen a captcha that requires more than 3 clicks.
        print("Verification page detected.  Trying to bypass...")
        time.sleep(2)
        clickCycle(driver)

    print("Enjoy the content!")

    #print(driver.html) # You can extract the content of the page.
    print("Title of the page: ", driver.title)

    time.sleep(5)
    driver.quit()


