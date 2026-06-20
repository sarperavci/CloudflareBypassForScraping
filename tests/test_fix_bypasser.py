import asyncio

import pytest

import cf_bypasser.core.bypasser as bp
from cf_bypasser.core.bypasser import CloakBypasser
from cf_bypasser.utils.misc import cache_key

_real_sleep = asyncio.sleep


@pytest.fixture(autouse=True)
def _fast_sleep(monkeypatch):
    # solve_cloudflare_challenge sleeps 5s+; collapse real-time waits, keep tiny ones
    async def quick(delay, *a, **k):
        await _real_sleep(min(delay, 0.05))
    monkeypatch.setattr(bp.asyncio, "sleep", quick)


CLEAR_HTML = "<html><body>cloudflare challenged passed. You are now a free bot.</body></html>"
BLOCK_HTML = "<html><body>Sorry, you have been blocked. Cloudflare Ray ID: abc error 1020</body></html>"
NON_CF_HTML = "<html><body>just a normal site</body></html>"
CHALLENGE_HTML = "<html><body>cloudflare just a moment please wait</body></html>"


class FakeResponse:
    def __init__(self, status=200):
        self.status = status


class FakePage:
    def __init__(self, html=CLEAR_HTML, title="ok", content_raises=False,
                 status=200, ua="FakeUA/1.0", frames=None):
        self._html = html
        self._title = title
        self._content_raises = content_raises
        self._status = status
        self._ua = ua
        self.url = "https://example.com"
        self.frames = frames or []
        self.default_timeout = None
        self.nav_timeout = None
        self.mouse = self

    def set_default_timeout(self, ms):
        self.default_timeout = ms

    def set_default_navigation_timeout(self, ms):
        self.nav_timeout = ms

    async def goto(self, url, **kwargs):
        return FakeResponse(self._status)

    async def title(self):
        return self._title

    async def content(self):
        if self._content_raises:
            raise RuntimeError("content read failed")
        return self._html

    async def evaluate(self, script):
        return self._ua

    async def click(self, *a, **k):
        return None


class FakeContext:
    def __init__(self, page, cookies=None):
        self.pages = [page]
        self._cookies = cookies or []
        self.closed = False
        self.added = []

    async def cookies(self):
        return self._cookies

    async def add_cookies(self, lst):
        self.added.extend(lst)

    async def new_page(self):
        return self.pages[0]

    async def close(self):
        self.closed = True


def make_bypasser(tmp_path):
    cache_file = str(tmp_path / "cache.json")
    b = CloakBypasser(max_retries=2, log=False, cache_file=cache_file)
    return b


def patch_launch(monkeypatch, context):
    async def fake_launch(**kwargs):
        return context
    monkeypatch.setattr(bp.cb, "launch_context_async", fake_launch)


@pytest.mark.asyncio
async def test_content_raises_returns_false(tmp_path):
    b = make_bypasser(tmp_path)
    page = FakePage(content_raises=True, title="ok")
    success, cf_detected, status = await b.solve_cloudflare_challenge("https://x.com", page)
    # content read failed and is_bypassed also reads content -> cannot confirm
    assert success is False


@pytest.mark.asyncio
async def test_block_page_not_bypassed(tmp_path):
    b = make_bypasser(tmp_path)
    page = FakePage(html=BLOCK_HTML, title="Access denied")
    assert await b.is_bypassed(page) is False
    success, cf_detected, _ = await b.solve_cloudflare_challenge("https://x.com", page)
    assert cf_detected is True
    assert success is False


@pytest.mark.asyncio
async def test_clear_non_cf_page_succeeds(tmp_path):
    b = make_bypasser(tmp_path)
    page = FakePage(html=NON_CF_HTML, title="home")
    assert await b.is_bypassed(page) is True
    success, cf_detected, _ = await b.solve_cloudflare_challenge("https://x.com", page)
    assert success is True
    assert cf_detected is False


@pytest.mark.asyncio
async def test_setup_browser_sets_timeouts(tmp_path, monkeypatch):
    b = make_bypasser(tmp_path)
    page = FakePage()
    ctx = FakeContext(page)
    patch_launch(monkeypatch, ctx)
    context, p = await b.setup_browser()
    assert p.default_timeout == bp.DEFAULT_TIMEOUT_MS
    assert p.nav_timeout == bp.DEFAULT_TIMEOUT_MS
    await b.cleanup_browser(context)


@pytest.mark.asyncio
async def test_cf_detected_no_clearance_not_cached(tmp_path, monkeypatch):
    b = make_bypasser(tmp_path)
    # CF detected (html has "cloudflare") and bypassed-looking, but no cf_clearance cookie
    page = FakePage(html="<html>cloudflare ok body</html>", title="ok")
    ctx = FakeContext(page, cookies=[{"name": "foo", "value": "bar"}])
    patch_launch(monkeypatch, ctx)
    result = await b.get_or_generate_cookies("https://example.com")
    assert result is None
    assert b.cookie_cache.get(cache_key("example.com", None)) is None


@pytest.mark.asyncio
async def test_real_clearance_is_cached(tmp_path, monkeypatch):
    b = make_bypasser(tmp_path)
    page = FakePage(html="<html>cloudflare ok body</html>", title="ok")
    ctx = FakeContext(page, cookies=[{"name": "cf_clearance", "value": "xyz"}])
    patch_launch(monkeypatch, ctx)
    result = await b.get_or_generate_cookies("https://example.com")
    assert result is not None
    assert result["cookies"]["cf_clearance"] == "xyz"
    assert b.cookie_cache.get(cache_key("example.com", None)) is not None


@pytest.mark.asyncio
async def test_non_cf_caches_without_clearance(tmp_path, monkeypatch):
    b = make_bypasser(tmp_path)
    page = FakePage(html=NON_CF_HTML, title="home")
    ctx = FakeContext(page, cookies=[{"name": "session", "value": "1"}])
    patch_launch(monkeypatch, ctx)
    result = await b.get_or_generate_cookies("https://example.com")
    assert result is not None
    assert b.cookie_cache.get(cache_key("example.com", None)) is not None


@pytest.mark.asyncio
async def test_concurrency_capped(tmp_path, monkeypatch):
    monkeypatch.setattr(bp, "_MAX_CONCURRENT_BROWSERS", 3)
    bp._browser_semaphores.clear()
    bp._inflight_locks.clear()

    live = 0
    peak = 0

    class TrackingContext(FakeContext):
        async def cookies(self_inner):
            await asyncio.sleep(0.05)
            return self_inner._cookies

    async def fake_launch(**kwargs):
        nonlocal live, peak
        live += 1
        peak = max(peak, live)
        await asyncio.sleep(0.05)
        page = FakePage(html=NON_CF_HTML, title="home")
        return TrackingContext(page, cookies=[{"name": "s", "value": "1"}])

    # wrap close to decrement
    orig_cleanup = CloakBypasser.cleanup_browser

    async def tracking_cleanup(self, context):
        nonlocal live
        live -= 1
        return await orig_cleanup(self, context)

    monkeypatch.setattr(CloakBypasser, "cleanup_browser", tracking_cleanup)
    monkeypatch.setattr(bp.cb, "launch_context_async", fake_launch)

    b = make_bypasser(tmp_path)
    urls = [f"https://site{i}.com" for i in range(12)]
    await asyncio.gather(*(b.get_or_generate_cookies(u) for u in urls))
    assert peak <= 3


@pytest.mark.asyncio
async def test_inflight_dedup(tmp_path, monkeypatch):
    bp._browser_semaphores.clear()
    bp._inflight_locks.clear()
    b = make_bypasser(tmp_path)

    launches = 0

    async def fake_launch(**kwargs):
        nonlocal launches
        launches += 1
        await asyncio.sleep(0.05)
        page = FakePage(html=NON_CF_HTML, title="home")
        return FakeContext(page, cookies=[{"name": "s", "value": "1"}])

    monkeypatch.setattr(bp.cb, "launch_context_async", fake_launch)

    r1, r2 = await asyncio.gather(
        b.get_or_generate_cookies("https://same.com"),
        b.get_or_generate_cookies("https://same.com"),
    )
    assert r1 is not None and r2 is not None
    assert launches == 1


@pytest.mark.asyncio
async def test_geoip_flag(tmp_path, monkeypatch):
    b = make_bypasser(tmp_path)
    page = FakePage()
    ctx = FakeContext(page)
    captured = {}

    async def fake_launch(**kwargs):
        captured.update(kwargs)
        return ctx

    monkeypatch.setattr(bp.cb, "launch_context_async", fake_launch)

    await b.setup_browser()
    assert captured["geoip"] is False
    await b.setup_browser(proxy="http://user:pass@1.2.3.4:8080")
    assert captured["geoip"] is True


@pytest.mark.asyncio
async def test_proxy_parse_failure_raises(tmp_path, monkeypatch):
    b = make_bypasser(tmp_path)
    monkeypatch.setattr(bp.cb, "launch_context_async",
                        lambda **k: (_ for _ in ()).throw(AssertionError("must not launch")))
    with pytest.raises(ValueError):
        await b.setup_browser(proxy="not-a-valid-proxy")


def test_cache_key_no_collision():
    a = cache_key("foo.com", "bar")
    b = cache_key("foo.comb", "ar")
    assert a != b


def _ip_check_setup(monkeypatch, ip_sequence):
    bp._browser_semaphores.clear()
    bp._inflight_locks.clear()
    monkeypatch.setattr(bp, "IP_CHECK_ENABLED", True)
    ips = iter(ip_sequence)

    async def fake_get_exit_ip(proxy=None):
        return next(ips)

    monkeypatch.setattr(bp, "get_exit_ip", fake_get_exit_ip)

    launches = {"n": 0}

    async def fake_launch(**kwargs):
        launches["n"] += 1
        page = FakePage(html=NON_CF_HTML, title="home")
        return FakeContext(page, cookies=[{"name": "cf_clearance", "value": "x"}])

    monkeypatch.setattr(bp.cb, "launch_context_async", fake_launch)
    return launches


@pytest.mark.asyncio
async def test_ip_check_invalidates_on_rotation(tmp_path, monkeypatch):
    # gen records 1.1.1.1; next read sees 2.2.2.2 (rotated) -> invalidate + regen records 2.2.2.2
    launches = _ip_check_setup(monkeypatch, ["1.1.1.1", "2.2.2.2", "2.2.2.2"])
    b = make_bypasser(tmp_path)
    assert await b.get_or_generate_cookies("https://site.com") is not None
    assert await b.get_or_generate_cookies("https://site.com") is not None
    assert launches["n"] == 2  # cache was invalidated and regenerated


@pytest.mark.asyncio
async def test_ip_check_keeps_cache_when_ip_stable(tmp_path, monkeypatch):
    # gen records 9.9.9.9; next read sees 9.9.9.9 (same) -> serve cache, no relaunch
    launches = _ip_check_setup(monkeypatch, ["9.9.9.9", "9.9.9.9"])
    b = make_bypasser(tmp_path)
    assert await b.get_or_generate_cookies("https://site.com") is not None
    assert await b.get_or_generate_cookies("https://site.com") is not None
    assert launches["n"] == 1  # cache reused
