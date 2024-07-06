import time
from DrissionPage import ChromiumPage 

# This code is written for readibility and simplicity. It is not optimized for performance or real-world usage.
# You can optimize the code by removing the unnecessary sleeps and checks.

class CloudflareBypasser:
    def __init__(self, driver: ChromiumPage):
        self.driver = driver

    def clickCycle(self):
        #reach the captcha button and click it
        # if iframe does not exist, it means the page is already bypassed.
        if self.driver.wait.ele_displayed('#turnstile-wrapper',timeout=1.5):
            time.sleep(1.5)
            self.driver.ele("#turnstile-wrapper", timeout=2.5).click()
            # The location of the button may vary time to time. I sometimes check the button's location and update the code.
 
    def isBypassed(self):
        title = self.driver.title.lower()
        # If the title does not contain "just a moment", it means the page is bypassed.
        # This is a simple check, you can implement more complex checks.
        return "just a moment" not in title

    def bypass(self):
        while not self.isBypassed():
            time.sleep(2)
            # A click may be enough to bypass the captcha, if your IP is clean.
            # I haven't seen a captcha that requires more than 3 clicks.
            print("Verification page detected.  Trying to bypass...")
            time.sleep(2)
            self.clickCycle()