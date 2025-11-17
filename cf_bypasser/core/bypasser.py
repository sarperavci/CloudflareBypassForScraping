import asyncio
import logging
import os
import random
from typing import Optional, Dict, Any
from urllib.parse import urlparse

from camoufox.async_api import AsyncCamoufox
from playwright_captcha import CaptchaType, ClickSolver, FrameworkType
from playwright_captcha.utils.camoufox_add_init_script.add_init_script import get_addon_path

from cf_bypasser.utils.misc import md5_hash
from cf_bypasser.cache.cookie_cache import CookieCache
from cf_bypasser.utils.config import BrowserConfig, OPERATING_SYSTEMS

# Get addon path for Camoufox init script workaround
ADDON_PATH = get_addon_path()


class CamoufoxBypasser:
    """Camoufox bypasser with cookie caching and direct proxy support."""
    
    def __init__(self, max_retries: int = 5, log: bool = True, cache_file: str = "cf_cookie_cache.json"):
        self.max_retries = max_retries
        self.log = log
        self.browser = None
        self.context = None
        self.page = None
        self.cookie_cache = CookieCache(cache_file)

    def log_message(self, message: str) -> None:
        """Log message if logging is enabled."""
        if self.log:
            logging.info(message)

    def parse_proxy(self, proxy: str) -> Optional[Dict[str, str]]:
        """Parse proxy URL and return proxy configuration."""
        try:
            parsed = urlparse(proxy)
            if not parsed.hostname or not parsed.port:
                self.log_message(f"Invalid proxy format: {proxy}")
                return None
            
            proxy_config = {
                "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
            }
            
            if parsed.username and parsed.password:
                proxy_config["username"] = parsed.username
                proxy_config["password"] = parsed.password
            
            return proxy_config
        except Exception as e:
            self.log_message(f"Error parsing proxy {proxy}: {e}")
            return None

    async def setup_browser(self, proxy: Optional[str] = None, lang: str = "en") -> None:
        """Setup Camoufox browser with random OS and configuration."""
        # Clear expired cache entries
        self.cookie_cache.clear_expired()
        
        # Randomly choose an OS
        selected_os = random.choice(OPERATING_SYSTEMS)
        self.log_message(f"Using OS: {selected_os}")
        
        # Generate random config for the selected OS
        random_config = BrowserConfig.generate_random_config(selected_os, lang=lang)
        self.log_message(f"Generated config with UA: {random_config.get('navigator.userAgent', 'N/A')}")
        self.log_message(f"Screen resolution: {random_config['window.outerWidth']}x{random_config['window.outerHeight']}")

        # Setup proxy configuration if provided
        proxy_config = None
        if proxy:
            proxy_config = self.parse_proxy(proxy)
            if proxy_config:
                self.log_message(f"Using proxy: {proxy_config['server']}")
            else:
                self.log_message("Failed to parse proxy, continuing without proxy")

        # Launch Camoufox with stealth settings
        self.browser = await AsyncCamoufox(
            headless=True,
            geoip=True if proxy else False,  # Auto-detect geolocation from proxy
            humanize=False,  # Humanize cursor movement
            os=selected_os,  # Random OS selection
            locale=lang if lang else "en-US",
            
            # Required for Camoufox add_init_script workaround
            i_know_what_im_doing=True,
            config={'forceScopeAccess': True, **random_config},
            disable_coop=True,  # Allows clicking Cloudflare checkbox
            main_world_eval=True,
            addons=[os.path.abspath(ADDON_PATH)],
            
            # Performance settings
            block_images=False,  # Keep images for realistic behavior
            block_webrtc=True,  # Block WebRTC for privacy
            enable_cache=False,  # Disable cache to save memory
        ).__aenter__()

        # Create context with proxy if provided
        context_options = {}
        if proxy_config:
            context_options["proxy"] = proxy_config

        self.context = await self.browser.new_context(**context_options)
        self.page = await self.context.new_page()

    async def is_bypassed(self) -> bool:
        """Check if Cloudflare challenge has been bypassed."""
        try:
            title = await self.page.title()
            html_content = await self.page.content()
            return "just a moment" not in title.lower() and "please complete the captcha" not in html_content.lower()
        except Exception as e:
            self.log_message(f"Error checking page title: {e}")
            return False
    
    async def determine_challenge_type(self) -> CaptchaType:
        """Determine the type of Cloudflare challenge present."""
        try:
            html_content = await self.page.content()
            title = await self.page.title()
            if "please complete the captcha" in html_content.lower():
                return CaptchaType.CLOUDFLARE_TURNSTILE
            elif "just a moment" in title.lower():
                return CaptchaType.CLOUDFLARE_INTERSTITIAL
            else:
                return None
        except Exception as e:
            self.log_message(f"Error determining challenge type: {e}")
            return None

    async def solve_cloudflare_challenge(self, url: str) -> bool:
        """Navigate to URL and solve Cloudflare challenge using playwright-captcha."""
        try:
            # Navigate to the target URL
            self.log_message(f"Navigating to {url}")
            await self.page.goto(url, wait_until="domcontentloaded", timeout=10000)
            
            # Wait for page to load
            await asyncio.sleep(8)

            # Check if we need to solve a challenge
            if await self.is_bypassed():
                self.log_message("No Cloudflare challenge detected or already bypassed")
                return True

            self.log_message("Cloudflare challenge detected. Attempting to solve...")
            challenge_type = await self.determine_challenge_type()
            if not challenge_type:
                self.log_message("Could not determine challenge type")
                return False
            
            expected_selector = "#root"
            captcha_container = self.page
            is_solved = False                
            async with ClickSolver(framework=FrameworkType.CAMOUFOX, page=self.page) as solver:
 
                await solver.solve_captcha(
                    captcha_container=captcha_container,
                    captcha_type=challenge_type,
                    expected_content_selector=expected_selector,)

                is_solved = "just a moment" not in await self.page.title()
            

            if is_solved:
                self.log_message("✅ Cloudflare challenge solved successfully!")
                # Wait a bit more to ensure cookies are set
                await asyncio.sleep(3)
                return True
            else:
                self.log_message("❌ Failed to solve Cloudflare challenge")
                return False

        except Exception as e:
            self.log_message(f"Error solving Cloudflare challenge: {e}")
            return False

    async def get_cookies_and_user_agent(self, url: str) -> Dict[str, Any]:
        """Get cookies and user agent after successful bypass."""
        try:
            cookies = await self.context.cookies()
            cookie_dict = {}
            for cookie in cookies:
                cookie_dict[cookie['name']] = cookie['value']
            
            # Get user agent from the page
            user_agent = await self.page.evaluate("navigator.userAgent")
            
            return {
                "cookies": cookie_dict,
                "user_agent": user_agent
            }
        except Exception as e:
            self.log_message(f"Error getting cookies and user agent: {e}")
            return None

    async def get_html_content_and_cookies(self, url: str) -> Dict[str, Any]:
        """Get HTML content, cookies, and user agent after successful bypass."""
        try:
            cookies = await self.context.cookies()
            cookie_dict = {}
            for cookie in cookies:
                cookie_dict[cookie['name']] = cookie['value']
            
            # Get user agent from the page
            user_agent = await self.page.evaluate("navigator.userAgent")
            
            # Get HTML content
            html_content = await self.page.content()
            
            # Get final URL (in case of redirects)
            final_url = self.page.url
            
            return {
                "cookies": cookie_dict,
                "user_agent": user_agent,
                "html": html_content,
                "url": final_url,
                "status_code": 200  # Assuming success if we got here
            }
        except Exception as e:
            self.log_message(f"Error getting HTML content and cookies: {e}")
            return None

    async def get_or_generate_cookies(self, url: str, proxy: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get cached cookies or generate new ones."""
        try:
            
            hostname = urlparse(url).netloc
            cache_key = md5_hash(hostname + proxy if proxy else "")            
            # Try to get cached cookies first
            cached = self.cookie_cache.get(cache_key)
            if cached:
                return {
                    "cookies": cached.cookies,
                    "user_agent": cached.user_agent
                }
            
            self.log_message(f"No cached cookies for {cache_key}, generating new ones...")
            
            # Setup browser and solve challenge
            await self.setup_browser(proxy)
            
            if await self.solve_cloudflare_challenge(url):
                data = await self.get_cookies_and_user_agent(url)
                if data and data["cookies"]:
                    # Cache the new cookies
                    self.cookie_cache.set(cache_key, data["cookies"], data["user_agent"])
                    return data
            
            return None
            
        except Exception as e:
            self.log_message(f"Error in get_or_generate_cookies: {e}")
            return None
        finally:
            await self.cleanup()

    async def get_or_generate_html(self, url: str, proxy: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get HTML content along with cookies (cached or fresh)."""
        try:
            hostname = urlparse(url).netloc
            cache_key = md5_hash(hostname + proxy if proxy else "")            
            
            # Try to get cached cookies first
            cached = self.cookie_cache.get(cache_key)
            
            # For HTML endpoint, we need to setup browser and get fresh content
            # even if we have cached cookies, as HTML content may change
            self.log_message(f"Getting HTML content for {url}...")
            
            # Setup browser and solve challenge
            await self.setup_browser(proxy)
            
            if await self.solve_cloudflare_challenge(url):
                data = await self.get_html_content_and_cookies(url)
                if data and data["cookies"]:
                    # Cache the cookies for future use
                    self.cookie_cache.set(cache_key, data["cookies"], data["user_agent"])
                    return data
            
            return None
            
        except Exception as e:
            self.log_message(f"Error in get_or_generate_html: {e}")
            return None
        finally:
            await self.cleanup()

    async def cleanup(self) -> None:
        """Clean up browser resources."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.__aexit__(None, None, None)
        except Exception as e:
            self.log_message(f"Error during cleanup: {e}")
        finally:
            self.page = None
            self.context = None
            self.browser = None