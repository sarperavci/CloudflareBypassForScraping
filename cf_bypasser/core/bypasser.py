import asyncio
import logging
import os
from typing import Optional, Dict, Any
from urllib.parse import urlparse

# Skip the per-launch PyPI version check (latency/offline-unfriendly in prod/CI)
os.environ.setdefault("CLOAKBROWSER_AUTO_UPDATE", "false")

import cloakbrowser as cb

from cf_bypasser.utils.misc import md5_hash, get_browser_init_lock
from cf_bypasser.cache.cookie_cache import CookieCache

# Native closed-shadow-root access via the patched Chromium — lets us read and
# click the Cloudflare Turnstile checkbox without injecting attachShadow patches.
FAKE_SHADOW_ARG = "--enable-blink-features=FakeShadowRoot"

# JS run inside the Turnstile iframe: walk open + closed shadow roots and return
# the checkbox centre relative to the iframe viewport.
_FIND_CHECKBOX_JS = """() => {
    function find(root){
        if(!root) return null;
        const direct = root.querySelector && root.querySelector('input[type=checkbox]');
        if(direct) return direct;
        for(const el of (root.querySelectorAll ? root.querySelectorAll('*') : [])){
            const sr = el.fakeShadowRoot || el.shadowRoot;
            if(sr){ const r = find(sr); if(r) return r; }
        }
        return null;
    }
    const cb = find(document);
    if(!cb) return {found:false};
    const r = cb.getBoundingClientRect();
    return {found:true, checked:cb.checked, x:r.x+r.width/2, y:r.y+r.height/2, w:r.width};
}"""


class CamoufoxBypasser:
    """Cloudflare bypasser backed by CloakBrowser (stealth Chromium) with cookie caching."""

    def __init__(self, max_retries: int = 5, log: bool = True, cache_file: str = "cf_cookie_cache.json"):
        self.max_retries = max_retries
        self.log = log
        self.cookie_cache = CookieCache(cache_file)

    def log_message(self, message: str) -> None:
        if self.log:
            logging.info(message)

    def parse_proxy(self, proxy: str) -> Optional[Dict[str, str]]:
        """Parse a proxy URL into a Playwright/CloakBrowser proxy dict."""
        try:
            parsed = urlparse(proxy)
            if not parsed.hostname or not parsed.port:
                self.log_message(f"Invalid proxy format: {proxy}")
                return None

            proxy_config = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
            if parsed.username and parsed.password:
                proxy_config["username"] = parsed.username
                proxy_config["password"] = parsed.password
            return proxy_config
        except Exception as e:
            self.log_message(f"Error parsing proxy {proxy}: {e}")
            return None

    async def setup_browser(self, proxy: Optional[str] = None, lang: str = "en", user_agent: Optional[str] = None, headless: bool = False) -> tuple:
        """Launch a fresh, profile-less CloakBrowser context. Returns (context, page)."""
        self.cookie_cache.clear_expired()

        proxy_config = None
        if proxy:
            proxy_config = self.parse_proxy(proxy)
            if proxy_config:
                self.log_message(f"Using proxy: {proxy_config['server']}")
            else:
                self.log_message("Failed to parse proxy, continuing without proxy")

        launch_kwargs = dict(
            headless=headless,
            args=[FAKE_SHADOW_ARG],
            geoip=bool(proxy),
            locale=lang if lang else None,
        )
        if proxy_config:
            launch_kwargs["proxy"] = proxy_config
        if user_agent:
            launch_kwargs["user_agent"] = user_agent

        context = None
        try:
            # browserforge fingerprint generation isn't thread-safe; serialize launches
            async with get_browser_init_lock():
                context = await cb.launch_context_async(**launch_kwargs)
            page = context.pages[0] if context.pages else await context.new_page()
            return context, page
        except BaseException:
            # a partial launch must never orphan a browser process,
            # even on cancellation/timeout (hence BaseException)
            await self.cleanup_browser(context)
            raise

    async def is_bypassed(self, page) -> bool:
        """Check if the Cloudflare challenge has been cleared."""
        try:
            title = await page.title()
            if "just a moment" in title.lower():
                return False
            html_content = await page.content()
            if "please complete the captcha" in html_content.lower():
                return False
            return True
        except Exception as e:
            self.log_message(f"Error checking bypass status: {e}")
            return False

    async def _click_turnstile_checkbox(self, page) -> bool:
        """Find the Turnstile checkbox via fakeShadowRoot and click it. Returns True if clicked."""
        cf_frames = [f for f in page.frames if "challenges.cloudflare" in (f.url or "")]
        for frame in cf_frames:
            try:
                info = await frame.evaluate(_FIND_CHECKBOX_JS)
                if not info.get("found") or info.get("w", 0) <= 0 or info.get("checked"):
                    continue
                frame_el = await frame.frame_element()
                box = await frame_el.bounding_box()
                if not box:
                    continue
                # checkbox coords are iframe-relative; offset by the iframe's page position
                await page.mouse.click(box["x"] + info["x"], box["y"] + info["y"])
                self.log_message("Clicked Turnstile checkbox via fakeShadowRoot")
                return True
            except Exception as e:
                self.log_message(f"Checkbox click attempt failed: {e}")
        return False

    async def solve_cloudflare_challenge(self, url: str, page) -> bool:
        """Navigate to URL and clear any Cloudflare challenge."""
        try:
            self.log_message(f"Navigating to {url}")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception as nav_err:
                self.log_message(f"Navigation warning: {nav_err}")

            # let the challenge scripts load before deciding it's unprotected
            await asyncio.sleep(5)
            try:
                html_content = await page.content()
            except Exception:
                html_content = ""

            if "cloudflare" not in html_content.lower():
                self.log_message("No Cloudflare protection detected -- either not protected or already bypassed")
                return True

            if await self.is_bypassed(page):
                self.log_message("No Cloudflare challenge detected or already bypassed")
                return True

            self.log_message("Cloudflare challenge detected. Waiting for resolution...")
            clicked = False
            for _ in range(self.max_retries):
                if await self.is_bypassed(page):
                    self.log_message("Cloudflare challenge solved successfully!")
                    return True
                # non-interactive challenges auto-resolve; interactive ones need one click
                if not clicked:
                    clicked = await self._click_turnstile_checkbox(page)
                await asyncio.sleep(3)

            if await self.is_bypassed(page):
                self.log_message("Cloudflare challenge solved successfully!")
                return True

            self.log_message("Failed to solve Cloudflare challenge")
            return False

        except Exception as e:
            self.log_message(f"Error solving Cloudflare challenge: {e}")
            return False

    async def get_cookies_and_user_agent(self, context, page) -> Optional[Dict[str, Any]]:
        try:
            cookies = await context.cookies()
            cookie_dict = {c["name"]: c["value"] for c in cookies}
            user_agent = await page.evaluate("navigator.userAgent")
            return {"cookies": cookie_dict, "user_agent": user_agent}
        except Exception as e:
            self.log_message(f"Error getting cookies and user agent: {e}")
            return None

    async def get_html_content_and_cookies(self, context, page) -> Optional[Dict[str, Any]]:
        try:
            cookies = await context.cookies()
            cookie_dict = {c["name"]: c["value"] for c in cookies}
            user_agent = await page.evaluate("navigator.userAgent")
            return {
                "cookies": cookie_dict,
                "user_agent": user_agent,
                "html": await page.content(),
                "url": page.url,
                "status_code": 200,
            }
        except Exception as e:
            self.log_message(f"Error getting HTML content and cookies: {e}")
            return None

    async def get_or_generate_cookies(self, url: str, proxy: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get cached cookies or generate new ones."""
        hostname = urlparse(url).netloc
        cache_key = md5_hash(hostname + (proxy or ""))

        cached = self.cookie_cache.get(cache_key)
        if cached:
            return {"cookies": cached.cookies, "user_agent": cached.user_agent}

        self.log_message(f"No cached cookies for {cache_key}, generating new ones...")

        context = None
        try:
            context, page = await self.setup_browser(proxy)

            if await self.solve_cloudflare_challenge(url, page):
                data = await self.get_cookies_and_user_agent(context, page)
                if data:
                    self.cookie_cache.set(cache_key, data["cookies"], data["user_agent"])
                    return data
            return None
        except Exception as e:
            self.log_message(f"Error in get_or_generate_cookies: {e}")
            return None
        finally:
            await self.cleanup_browser(context)

    async def get_or_generate_html(self, url: str, proxy: Optional[str] = None, bypass_cache: bool = False) -> Optional[Dict[str, Any]]:
        """Get HTML content along with cookies (cached or fresh)."""
        hostname = urlparse(url).netloc
        cache_key = md5_hash(hostname + (proxy or ""))

        self.log_message(f"Getting HTML content for {url}...")

        cached_cookies = None
        cached_ua = None
        if not bypass_cache:
            cached = self.cookie_cache.get(cache_key)
            if cached:
                cached_cookies = cached.cookies
                cached_ua = cached.user_agent
                self.log_message(f"Found cached cookies for {url}")

        context = None
        try:
            context, page = await self.setup_browser(proxy, user_agent=cached_ua)

            if cached_cookies:
                self.log_message("Restoring cached cookies...")
                cookie_list = [{"name": name, "value": value, "url": url} for name, value in cached_cookies.items()]
                await context.add_cookies(cookie_list)

            if await self.solve_cloudflare_challenge(url, page):
                data = await self.get_html_content_and_cookies(context, page)
                if data:
                    self.cookie_cache.set(cache_key, data["cookies"], data["user_agent"])
                    return data
            return None
        except Exception as e:
            self.log_message(f"Error in get_or_generate_html: {e}")
            return None
        finally:
            await self.cleanup_browser(context)

    async def cleanup_browser(self, context) -> None:
        """Close the context (and its underlying browser). Never raises; never leaks."""
        if context is not None:
            try:
                # shield+timeout so a hung close (or outer cancellation) can't
                # leave the browser process running or block us forever
                await asyncio.wait_for(asyncio.shield(context.close()), timeout=30)
            except Exception as e:
                self.log_message(f"Error closing context: {e}")

    async def cleanup(self) -> None:
        """Backward compatibility method - no longer stores browser instances."""
        pass
