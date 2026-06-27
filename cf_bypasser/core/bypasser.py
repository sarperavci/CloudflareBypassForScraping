import asyncio
import logging
import os
from collections import namedtuple
from typing import Optional, Dict, Any
from urllib.parse import urlparse

# Skip the per-launch PyPI version check (latency/offline-unfriendly in prod/CI)
os.environ.setdefault("CLOAKBROWSER_AUTO_UPDATE", "false")

import cloakbrowser as cb

from cf_bypasser.utils.misc import cache_key, get_browser_init_lock, per_loop
from cf_bypasser.utils.constants import (
    DEFAULT_TIMEOUT_MS,
    CHALLENGE_SETTLE_SECONDS,
    HTML_SETTLE_POLL_SECONDS,
    HTML_SETTLE_STABLE_ROUNDS,
    HTML_SETTLE_MAX_SECONDS,
    RETRY_POLL_SECONDS,
    CONTEXT_CLOSE_TIMEOUT_SECONDS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_CACHE_FILE,
    MAX_CONCURRENT_BROWSERS,
    IP_CHECK_ENABLED,
)
from cf_bypasser.utils.ipcheck import get_exit_ip
from cf_bypasser.cache.cookie_cache import CookieCache

_MAX_CONCURRENT_BROWSERS = MAX_CONCURRENT_BROWSERS

# One semaphore + one in-flight lock registry per event loop (multi-loop pytest safe).
_browser_semaphores: dict = {}
_inflight_locks: dict = {}

ChallengeResult = namedtuple("ChallengeResult", ("success", "cf_detected", "status"))


def _browser_semaphore() -> asyncio.Semaphore:
    # read _MAX_CONCURRENT_BROWSERS at creation time so monkeypatching it takes effect
    return per_loop(_browser_semaphores, lambda: asyncio.Semaphore(_MAX_CONCURRENT_BROWSERS))


def _inflight_lock(key: str) -> asyncio.Lock:
    registry = per_loop(_inflight_locks, dict)
    lock = registry.get(key)
    if lock is None:
        lock = asyncio.Lock()
        registry[key] = lock
    return lock

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


class CloakBypasser:
    """Cloudflare bypasser backed by CloakBrowser (stealth Chromium) with cookie caching."""

    def __init__(self, max_retries: int = DEFAULT_MAX_RETRIES, log: bool = True, cache_file: str = DEFAULT_CACHE_FILE):
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
                # never silently fall back to direct: that leaks the real IP
                raise ValueError(f"Invalid proxy, refusing to continue direct: {proxy}")

        launch_kwargs = dict(
            headless=headless,
            args=[FAKE_SHADOW_ARG],
            geoip=bool(proxy_config),
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
            page.set_default_timeout(DEFAULT_TIMEOUT_MS)
            page.set_default_navigation_timeout(DEFAULT_TIMEOUT_MS)
            return context, page
        except BaseException:
            # a partial launch must never orphan a browser process,
            # even on cancellation/timeout (hence BaseException)
            await self.cleanup_browser(context)
            raise

    # block-specific phrases; "cloudflare ray id" alone is NOT enough (legit footers have it)
    _BLOCK_MARKERS = (
        "you have been blocked",
        "sorry, you have been blocked",
        "error 1020",
        "access denied",
    )

    async def is_bypassed(self, page) -> bool:
        """Check if the Cloudflare challenge has been cleared (and not a block page)."""
        try:
            title = await page.title()
            if "just a moment" in title.lower():
                return False
            html_content = await page.content()
            lowered = html_content.lower()
            if "please complete the captcha" in lowered:
                return False
            if any(marker in lowered for marker in self._BLOCK_MARKERS):
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
                # only count it as clicked if the box became checked or disappeared
                after = await frame.evaluate(_FIND_CHECKBOX_JS)
                if (not after.get("found")) or after.get("checked"):
                    self.log_message("Clicked Turnstile checkbox via fakeShadowRoot")
                    return True
                self.log_message("Turnstile checkbox click did not register, retrying")
            except Exception as e:
                self.log_message(f"Checkbox click attempt failed: {e}")
        return False

    async def solve_cloudflare_challenge(self, url: str, page) -> tuple:
        """Navigate to URL and clear any Cloudflare challenge. Returns (success, cf_detected, status)."""
        cf_detected = False
        status = 200
        try:
            self.log_message(f"Navigating to {url}")
            try:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT_MS)
                if response is not None and getattr(response, "status", None):
                    status = response.status
            except Exception as nav_err:
                self.log_message(f"Navigation warning: {nav_err}")

            # let the challenge scripts load before deciding it's unprotected
            await asyncio.sleep(CHALLENGE_SETTLE_SECONDS)
            try:
                html_content = await page.content()
                content_ok = True
            except Exception:
                html_content = ""
                content_ok = False

            if not content_ok:
                # a failed read tells us nothing; never claim success on empty content
                self.log_message("Could not read page content -- treating as unconfirmed")
                bypassed = await self.is_bypassed(page)
                return ChallengeResult(bypassed, cf_detected, status)

            if "cloudflare" not in html_content.lower():
                self.log_message("No Cloudflare protection detected -- either not protected or already bypassed")
                return ChallengeResult(True, cf_detected, status)

            cf_detected = True
            if await self.is_bypassed(page):
                self.log_message("No Cloudflare challenge detected or already bypassed")
                return ChallengeResult(True, cf_detected, status)

            self.log_message("Cloudflare challenge detected. Waiting for resolution...")
            clicked = False
            for _ in range(self.max_retries):
                if await self.is_bypassed(page):
                    self.log_message("Cloudflare challenge solved successfully!")
                    return ChallengeResult(True, cf_detected, status)
                # non-interactive challenges auto-resolve; interactive ones need one click
                if not clicked:
                    clicked = await self._click_turnstile_checkbox(page)
                await asyncio.sleep(RETRY_POLL_SECONDS)

            if await self.is_bypassed(page):
                self.log_message("Cloudflare challenge solved successfully!")
                return ChallengeResult(True, cf_detected, status)

            self.log_message("Failed to solve Cloudflare challenge")
            return ChallengeResult(False, cf_detected, status)

        except Exception as e:
            self.log_message(f"Error solving Cloudflare challenge: {e}")
            return ChallengeResult(False, cf_detected, status)

    async def get_cookies_and_user_agent(self, context, page) -> Optional[Dict[str, Any]]:
        try:
            cookies = await context.cookies()
            cookie_dict = {c["name"]: c["value"] for c in cookies}
            user_agent = await page.evaluate("navigator.userAgent")
            return {"cookies": cookie_dict, "user_agent": user_agent}
        except Exception as e:
            self.log_message(f"Error getting cookies and user agent: {e}")
            return None

    async def _stable_html(self, page) -> str:
        """Return page.content() once its size stops changing, so JS renders deterministically.

        Polls instead of relying on networkidle (Playwright has no networkidle2 and idle
        can hang on pages with persistent connections). Bounded by HTML_SETTLE_MAX_SECONDS.
        """
        try:
            await page.wait_for_load_state("load", timeout=DEFAULT_TIMEOUT_MS)
        except Exception:
            pass

        html = await page.content()
        if HTML_SETTLE_STABLE_ROUNDS <= 0 or HTML_SETTLE_POLL_SECONDS <= 0:
            return html

        deadline = asyncio.get_event_loop().time() + HTML_SETTLE_MAX_SECONDS
        stable = 0
        while stable < HTML_SETTLE_STABLE_ROUNDS and asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(HTML_SETTLE_POLL_SECONDS)
            try:
                current = await page.content()
            except Exception:
                break
            if len(current) == len(html):
                stable += 1
            else:
                stable = 0
            html = current
        return html

    async def get_html_content_and_cookies(self, context, page, status_code: int = 200) -> Optional[Dict[str, Any]]:
        try:
            html = await self._stable_html(page)
            cookies = await context.cookies()
            cookie_dict = {c["name"]: c["value"] for c in cookies}
            user_agent = await page.evaluate("navigator.userAgent")
            return {
                "cookies": cookie_dict,
                "user_agent": user_agent,
                "html": html,
                "url": page.url,
                "status_code": status_code,
            }
        except Exception as e:
            self.log_message(f"Error getting HTML content and cookies: {e}")
            return None

    @staticmethod
    def _is_trustworthy(cookies: Dict[str, str], cf_detected: bool) -> bool:
        """A CF-detected result is only trustworthy once a cf_clearance cookie exists."""
        if not cf_detected:
            return True
        return bool(cookies.get("cf_clearance"))

    async def _read_valid_cache(self, key: str, proxy: Optional[str]):
        """Return a still-valid cache entry, or None — invalidating it if the proxy exit IP rotated."""
        cached = self.cookie_cache.get(key)
        if not cached:
            return None
        if IP_CHECK_ENABLED and cached.exit_ip:
            current = await get_exit_ip(proxy)
            if current and current != cached.exit_ip:
                self.log_message(f"Proxy exit IP changed ({cached.exit_ip} -> {current}); invalidating cookies for {key}")
                self.cookie_cache.invalidate(key)
                return None
        return cached

    async def _run_in_browser(self, url, proxy, key, *, restore_cookies, extractor):
        """Shared browser skeleton: launch, solve, extract, cache. Returns the extractor dict or None."""
        cached_ua = None
        cached_cookies = None
        if restore_cookies:
            cached = await self._read_valid_cache(key, proxy)
            if cached:
                cached_cookies = cached.cookies
                cached_ua = cached.user_agent
                self.log_message(f"Found cached cookies for {url}")

        async with _browser_semaphore():
            context = None
            try:
                context, page = await self.setup_browser(proxy, user_agent=cached_ua)

                if cached_cookies:
                    self.log_message("Restoring cached cookies...")
                    cookie_list = [{"name": name, "value": value, "url": url} for name, value in cached_cookies.items()]
                    await context.add_cookies(cookie_list)

                result = await self.solve_cloudflare_challenge(url, page)
                success, cf_detected, status = result
                if success:
                    data = await extractor(context, page, status)
                    if data and self._is_trustworthy(data["cookies"], cf_detected):
                        exit_ip = await get_exit_ip(proxy) if IP_CHECK_ENABLED else None
                        self.cookie_cache.set(key, data["cookies"], data["user_agent"], exit_ip=exit_ip)
                        return data
                    if data:
                        self.log_message("CF detected but no cf_clearance cookie -- not caching")
                return None
            except Exception as e:
                self.log_message(f"Error running browser for {url}: {e}")
                return None
            finally:
                await self.cleanup_browser(context)

    async def get_or_generate_cookies(self, url: str, proxy: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get cached cookies or generate new ones."""
        hostname = urlparse(url).netloc
        key = cache_key(hostname, proxy)

        cached = await self._read_valid_cache(key, proxy)
        if cached:
            return {"cookies": cached.cookies, "user_agent": cached.user_agent}

        async with _inflight_lock(key):
            # another waiter may have populated the cache while we queued
            cached = await self._read_valid_cache(key, proxy)
            if cached:
                return {"cookies": cached.cookies, "user_agent": cached.user_agent}

            self.log_message(f"No cached cookies for {key}, generating new ones...")

            async def extractor(context, page, status):
                return await self.get_cookies_and_user_agent(context, page)

            return await self._run_in_browser(url, proxy, key, restore_cookies=False, extractor=extractor)

    async def get_or_generate_html(self, url: str, proxy: Optional[str] = None, bypass_cache: bool = False) -> Optional[Dict[str, Any]]:
        """Get HTML content along with cookies (cached or fresh)."""
        hostname = urlparse(url).netloc
        key = cache_key(hostname, proxy)

        self.log_message(f"Getting HTML content for {url}...")

        # No in-flight lock here: HTML must be fetched fresh per request, so concurrent
        # requests run in parallel (bounded by the semaphore) rather than serializing.
        async def extractor(context, page, status):
            return await self.get_html_content_and_cookies(context, page, status_code=status)

        return await self._run_in_browser(url, proxy, key, restore_cookies=not bypass_cache, extractor=extractor)

    async def cleanup_browser(self, context) -> None:
        """Close the context (and its underlying browser). Never raises; never leaks."""
        if context is not None:
            try:
                # shield+timeout so a hung close (or outer cancellation) can't
                # leave the browser process running or block us forever
                await asyncio.wait_for(asyncio.shield(context.close()), timeout=CONTEXT_CLOSE_TIMEOUT_SECONDS)
            except Exception as e:
                self.log_message(f"Error closing context: {e}")

    async def cleanup(self) -> None:
        """Backward compatibility method - no longer stores browser instances."""
        pass
