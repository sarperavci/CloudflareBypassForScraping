from typing import Dict

from cf_bypasser.utils.constants import CHROME_HEADERS


class BrowserConfig:

    @staticmethod
    def get_chrome_headers() -> Dict[str, str]:
        """Chrome-like headers to pair with curl_cffi chrome impersonation on replayed requests."""
        return CHROME_HEADERS
