import time
from DrissionPage import ChromiumPage


# This code is written for readibility and simplicity. It is not optimized for performance or real-world usage.
# You can optimize the code by removing the unnecessary sleeps and checks.

class CloudflareBypasser:
    def __init__(self, driver: ChromiumPage, max_retries=-1, log=True):
        self.max_retries = max_retries
        self.log = log
        self.driver = driver

    def clickCycle(self):
        #reach the captcha button and click it
        # if iframe does not exist, it means the page is already bypassed.
        if self.driver.wait.ele_displayed('.spacer', timeout=1.5):
            time.sleep(1.5)
            self.driver.ele(".spacer", timeout=2.5).click()
            # The location of the button may vary time to time. I sometimes check the button's location and update the code.

    def isBypassed(self):
        title = self.driver.title.lower()
        # If the title does not contain "just a moment", it means the page is bypassed.
        # This is a simple check, you can implement more complex checks.
        return "just a moment" not in title

    def bypass(self):
        count = 0
        while not self.isBypassed():
            if 0 < self.max_retries + 1 <= count:
                if self.log:
                    print("Exceeded maximum tries")
                break
            time.sleep(2)
            # A click may be enough to bypass the captcha, if your IP is clean.
            # I haven't seen a captcha that requires more than 3 clicks.
            if self.log:
                print("Verification page detected.  Trying to bypass...")
            time.sleep(2)
            self.clickCycle()
            count += 1
