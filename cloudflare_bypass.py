# -*- coding:utf-8 -*-
import time
from DrissionPage import ChromiumPage, ChromiumOptions


def pass_cycle(_driver: ChromiumPage):
    """Pass"""
    try:
        if _driver('xpath://div/iframe').s_ele("xpath://input[@type='checkbox']") is not None:
            _driver('xpath://div/iframe').ele("xpath://input[@type='checkbox']", timeout=0.1).click()
    except:
        pass


if __name__ == '__main__':
    # Chromium Browser Path
    browser_path = "/usr/bin/google-chrome"

    options = ChromiumOptions()
    options.set_paths(browser_path=browser_path)

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
        "-disable-gpu"
        # "-headless=new"
        # "-incognito"
    ]

    for argument in arguments:
        options.set_argument(argument)

    driver = ChromiumPage(addr_driver_opts=options)

    driver.get('https://nowsecure.nl')

    # Pass Cloudflare
    while True:
        pass_cycle(driver)
        try:
            ele = driver.s_ele('xpath://h3')
            if ele.text == "nowSecure.nl":
                break
        except:
            time.sleep(.1)
    time.sleep(5)
 
    driver.quit()
    print("Done")