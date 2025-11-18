import asyncio
import logging
import os
import random
import time
from typing import Optional, Dict, Any
from urllib.parse import urlparse

from camoufox.async_api import AsyncCamoufox
from playwright_captcha import CaptchaType, ClickSolver, FrameworkType
from playwright_captcha.utils.camoufox_add_init_script.add_init_script import get_addon_path

from cf_bypasser.utils.misc import md5_hash, get_browser_init_lock
from cf_bypasser.cache.cookie_cache import CookieCache
from cf_bypasser.utils.config import BrowserConfig, OPERATING_SYSTEMS

# Get addon path for Camoufox init script workaround
ADDON_PATH = get_addon_path()


class CamoufoxBypasser:
    """Camoufox bypasser with cookie caching and direct proxy support."""
    
    def __init__(self, max_retries: int = 5, log: bool = True, cache_file: str = "cf_cookie_cache.json"):
        self.max_retries = max_retries
        self.log = log
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

    async def setup_browser(self, proxy: Optional[str] = None, lang: str = "en", user_agent: Optional[str] = None) -> tuple:
        """Setup Camoufox browser with random OS and configuration. Returns (browser, context, page)."""
        # Clear expired cache entries
        self.cookie_cache.clear_expired()
        
        # Determine OS from user_agent if provided, otherwise random
        selected_os = None
        if user_agent:
            ua_lower = user_agent.lower()
            if "windows" in ua_lower:
                selected_os = "windows"
            elif "macintosh" in ua_lower or "mac os" in ua_lower:
                selected_os = "macos"
            elif "linux" in ua_lower or "x11" in ua_lower:
                selected_os = "linux"
        
        if not selected_os:
            selected_os = random.choice(OPERATING_SYSTEMS)
            
        self.log_message(f"Using OS: {selected_os}")
        
        # Generate random config for the selected OS
        random_config = BrowserConfig.generate_random_config(selected_os, lang=lang)
        
        # Override user agent if provided
        if user_agent:
            random_config['navigator.userAgent'] = user_agent
            self.log_message(f"Using provided User-Agent: {user_agent}")
        else:
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

        # Use global lock to serialize browser initialization (browserforge is not thread-safe)
        async with get_browser_init_lock():
            browser = await AsyncCamoufox(
                headless=True,
                geoip=True if proxy else False,
                humanize=False,
                os=selected_os,
                locale=lang if lang else "en-US",
                i_know_what_im_doing=True,
                config={'forceScopeAccess': True, **random_config},
                disable_coop=True,
                main_world_eval=True,
                addons=[os.path.abspath(ADDON_PATH)],
                block_images=False,
                block_webrtc=True,
                enable_cache=False,
            ).__aenter__()

        # Create context with proxy if provided
        context_options = {}
        if proxy_config:
            context_options["proxy"] = proxy_config

        context = await browser.new_context(**context_options)
        page = await context.new_page()
        
        return browser, context, page

    async def is_bypassed(self, page) -> bool:
        """Check if Cloudflare challenge has been bypassed."""
        try:
            title = await page.title()
            html_content = await page.content()
            return "just a moment" not in title.lower() and "please complete the captcha" not in html_content.lower()
        except Exception as e:
            self.log_message(f"Error checking page title: {e}")
            return False
    
    async def determine_challenge_type(self, page) -> CaptchaType:
        """Determine the type of Cloudflare challenge present."""
        try:
            html_content = await page.content()
            title = await page.title()
            if "please complete the captcha" in html_content.lower():
                return CaptchaType.CLOUDFLARE_TURNSTILE
            elif "just a moment" in title.lower():
                return CaptchaType.CLOUDFLARE_INTERSTITIAL
            else:
                return None
        except Exception as e:
            self.log_message(f"Error determining challenge type: {e}")
            return None

    async def solve_cloudflare_challenge(self, url: str, page) -> bool:
        """Navigate to URL and solve Cloudflare challenge using playwright-captcha."""
        try:
            # Navigate to the target URL
            self.log_message(f"Navigating to {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=10000)
            
            # Wait for page to load
            await asyncio.sleep(8)

            # Check if we need to solve a challenge
            if await self.is_bypassed(page):
                self.log_message("No Cloudflare challenge detected or already bypassed")
                return True

            self.log_message("Cloudflare challenge detected. Attempting to solve...")
            challenge_type = await self.determine_challenge_type(page)
            if not challenge_type:
                self.log_message("Could not determine challenge type")
                return False
            
            expected_selector = "#root"
            captcha_container = page
            is_solved = False                
            async with ClickSolver(framework=FrameworkType.CAMOUFOX, page=page, max_attempts=2, attempt_delay=1) as solver:
 
                await solver.solve_captcha(
                    captcha_container=captcha_container,
                    captcha_type=challenge_type,
                    expected_content_selector=expected_selector,)

                is_solved = "just a moment" not in await page.title()
            

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

    async def get_cookies_and_user_agent(self, context, page) -> Dict[str, Any]:
        """Get cookies and user agent after successful bypass."""
        try:
            cookies = await context.cookies()
            cookie_dict = {}
            for cookie in cookies:
                cookie_dict[cookie['name']] = cookie['value']
            
            # Get user agent from the page
            user_agent = await page.evaluate("navigator.userAgent")
            
            return {
                "cookies": cookie_dict,
                "user_agent": user_agent
            }
        except Exception as e:
            self.log_message(f"Error getting cookies and user agent: {e}")
            return None

    async def get_html_content_and_cookies(self, context, page) -> Dict[str, Any]:
        """Get HTML content, cookies, and user agent after successful bypass."""
        try:
            cookies = await context.cookies()
            cookie_dict = {}
            for cookie in cookies:
                cookie_dict[cookie['name']] = cookie['value']
            
            # Get user agent from the page
            user_agent = await page.evaluate("navigator.userAgent")
            
            # Get HTML content
            html_content = await page.content()
            
            # Get final URL (in case of redirects)
            final_url = page.url
            
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
        
        # Create isolated browser instance
        browser = None
        context = None
        page = None
        
        try:
            # Setup browser and solve challenge
            browser, context, page = await self.setup_browser(proxy)
            
            if await self.solve_cloudflare_challenge(url, page):
                data = await self.get_cookies_and_user_agent(context, page)
                if data and data["cookies"]:
                    # Cache the new cookies
                    self.cookie_cache.set(cache_key, data["cookies"], data["user_agent"])
                    return data
            
            return None
            
        except Exception as e:
            self.log_message(f"Error in get_or_generate_cookies: {e}")
            return None
        finally:
            await self.cleanup_browser(browser, context, page)

    async def get_or_generate_html(self, url: str, proxy: Optional[str] = None, bypass_cache: bool = False) -> Optional[Dict[str, Any]]:
        """Get HTML content along with cookies (cached or fresh)."""
        hostname = urlparse(url).netloc
        cache_key = md5_hash(hostname + proxy if proxy else "")
        
        # For HTML endpoint, we need to setup browser and get fresh content
        # even if we have cached cookies, as HTML content may change
        self.log_message(f"Getting HTML content for {url}...")
        
        cached_cookies = None
        cached_ua = None
        
        if not bypass_cache:
            cached = self.cookie_cache.get(cache_key)
            if cached:
                cached_cookies = cached.cookies
                cached_ua = cached.user_agent
                self.log_message(f"Found cached cookies for {url}")

        # Create isolated browser instance
        browser = None
        context = None
        page = None
        
        try:
            # Setup browser and solve challenge
            browser, context, page = await self.setup_browser(proxy, user_agent=cached_ua)
            
            if cached_cookies:
                self.log_message("Restoring cached cookies...")
                # Convert dict to list of cookie objects
                cookie_list = []
                for name, value in cached_cookies.items():
                    cookie_list.append({
                        'name': name,
                        'value': value,
                        'url': url  # Use the target URL for the cookie
                    })
                await context.add_cookies(cookie_list)
            
            if await self.solve_cloudflare_challenge(url, page):
                data = await self.get_html_content_and_cookies(context, page)
                if data and data["cookies"]:
                    # Cache the cookies for future use
                    self.cookie_cache.set(cache_key, data["cookies"], data["user_agent"])
                    return data
            
            return None
            
        except Exception as e:
            self.log_message(f"Error in get_or_generate_html: {e}")
            return None
        finally:
            await self.cleanup_browser(browser, context, page)

    async def cleanup_browser(self, browser, context, page) -> None:
        """Clean up browser resources."""
        try:
            # Close page first
            if page:
                try:
                    await page.close()
                except Exception as e:
                    self.log_message(f"Error closing page: {e}")
                
            # Close context second
            if context:
                try:
                    await context.close()
                except Exception as e:
                    self.log_message(f"Error closing context: {e}")
                
            # Close browser last
            if browser:
                try:
                    await browser.__aexit__(None, None, None)
                except Exception as e:
                    self.log_message(f"Error closing browser: {e}")
                    
        except Exception as e:
            self.log_message(f"Error during cleanup: {e}")

    async def cleanup(self) -> None:
        """Backward compatibility method - no longer stores browser instances."""
        pass