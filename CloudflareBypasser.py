import time
from DrissionPage import ChromiumPage
from DrissionPage.common import Actions

class CloudflareBypasser:
    def __init__(self, driver: ChromiumPage, max_retries=-1, log=True):
        self.driver = driver
        self.max_retries = max_retries
        self.log = log
        self.actions = Actions(self.driver)
        
    def log_message(self, message):
        if self.log:
            print(message)

    def click_verification_button(self):
        try:
            if self.driver.wait.ele_displayed('#GBddK6', timeout=1.5):
                self.log_message("Verification button found. Attempting to interact.")
                self.actions.move_to("#GBddK6", duration=0.5).left(120).hold().wait(0.01, 0.15).release()
        except Exception as e:
            self.log_message(f"Error interacting with verification button: {e}")

    def is_bypassed(self):
        try:
            title = self.driver.title.lower()
            return "just a moment" not in title
        except Exception as e:
            self.log_message(f"Error checking page title: {e}")
            return False

    def bypass(self):
        try_count = 0
        while not self.is_bypassed():
            if 0 < self.max_retries + 1 <= try_count:
                self.log_message("Exceeded maximum retries. Bypass failed.")
                break
            self.log_message(f"Attempt {try_count + 1}: Verification page detected. Trying to bypass...")
            self.click_verification_button()
            try_count += 1
            time.sleep(2)
        if self.is_bypassed():
            self.log_message("Bypass successful.")
        else:
            self.log_message("Bypass failed.")
