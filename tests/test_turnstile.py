import asyncio
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from cf_bypasser.core.bypasser import CFBypasser
from cf_bypasser.core.turnstile import (
    TurnstileResult,
    inject_and_solve_turnstile,
    render_turnstile_html,
)
from cf_bypasser.server.app import create_app
from cf_bypasser.server.models import TurnstileRequest, TurnstileResponse


# ---------------------------------------------------------------------------
# HTML generation tests
# ---------------------------------------------------------------------------

def test_render_turnstile_html_basic():
    html = render_turnstile_html("0x4AAAAAAtestkey")
    assert "https://challenges.cloudflare.com/turnstile/v0/api.js" in html
    assert '"0x4AAAAAAtestkey"' in html
    assert "id=\"turnstile-container\"" in html
    assert "turnstile.render" in html
    assert "window.turnstileToken" in html
    assert "null" in html  # action, cdata, pagedata are null by default


def test_render_turnstile_html_with_parameters():
    html = render_turnstile_html(
        sitekey="0x4AAAAAAtestkey",
        action="login_flow",
        cdata="custom_payload_123",
        pagedata="page_data_xyz",
    )
    assert '"0x4AAAAAAtestkey"' in html
    assert '"login_flow"' in html
    assert '"custom_payload_123"' in html
    assert '"page_data_xyz"' in html
    assert "params.action = action" in html
    assert "params.cData = cdata" in html
    assert "params.chlPageData = pagedata" in html


def test_render_turnstile_html_escaping():
    # Quotes and special characters must be properly escaped
    html = render_turnstile_html(
        sitekey='key"with\'quotes',
        action='act</script><script>alert(1)</script>',
        cdata='cdata"\'\n',
    )
    assert 'key\\"with\'quotes' in html
    assert "</script><script>" not in html or r"\u003c/script\u003e" in html or r"<\/script>" in html or r"\n" in html


# ---------------------------------------------------------------------------
# Mock Tab solving tests
# ---------------------------------------------------------------------------

class FakeDriver:
    def __init__(self):
        self.callbacks = {}
        self.runs = []

    def set_callback(self, event, handler, immediate=False):
        self.callbacks[event] = handler

    def run(self, cmd, **kwargs):
        self.runs.append((cmd, kwargs))
        return {}


class FakeTurnstileTab:
    def __init__(self, token="token-12345", error=None, delay_rounds=0):
        self.driver = FakeDriver()
        self.url = "https://example.com/login"
        self._token = token
        self._error = error
        self._delay_rounds = delay_rounds
        self._rounds = 0
        self.got_urls = []

    def run_cdp(self, cmd, **kwargs):
        return {}

    def _run_cdp(self, cmd, **kwargs):
        return {"root": {"backendNodeId": 1, "nodeName": "#document", "children": []}}

    def get(self, url, retry=0, timeout=30):
        self.got_urls.append(url)
        return True

    def run_js(self, js, *args):
        if "return Boolean(window.turnstileRendered" in js:
            return True
        if "return window.turnstileToken" in js:
            self._rounds += 1
            if self._rounds > self._delay_rounds:
                return self._token
            return None
        if "return window.turnstileError" in js:
            return self._error
        return None


def test_inject_and_solve_turnstile_immediate_success(monkeypatch):
    monkeypatch.setattr("cf_bypasser.core.turnstile.sleep", lambda s: None)
    tab = FakeTurnstileTab(token="TEST_TOKEN_ABCD")
    res = inject_and_solve_turnstile(
        tab,
        url="https://example.com/form",
        sitekey="0x4AAAAAAtest",
        timeout=5.0,
        poll_interval=0.01,
    )
    assert res.success is True
    assert res.token == "TEST_TOKEN_ABCD"
    assert res.error is None
    assert "https://example.com/form" in tab.got_urls


def test_inject_and_solve_turnstile_error(monkeypatch):
    monkeypatch.setattr("cf_bypasser.core.turnstile.sleep", lambda s: None)
    tab = FakeTurnstileTab(token=None, error="300030")
    res = inject_and_solve_turnstile(
        tab,
        url="https://example.com/form",
        sitekey="0x4AAAAAAtest",
        timeout=5.0,
        poll_interval=0.01,
    )
    assert res.success is False
    assert res.token is None
    assert res.error == "300030"


def test_inject_and_solve_turnstile_timeout(monkeypatch):
    monkeypatch.setattr("cf_bypasser.core.turnstile.sleep", lambda s: None)
    tab = FakeTurnstileTab(token=None, error=None)
    res = inject_and_solve_turnstile(
        tab,
        url="https://example.com/form",
        sitekey="0x4AAAAAAtest",
        timeout=0.05,
        poll_interval=0.01,
    )
    assert res.success is False
    assert res.token is None
    assert res.error == "timeout"


def test_inject_and_solve_turnstile_interactive_click(monkeypatch):
    monkeypatch.setattr("cf_bypasser.core.turnstile.sleep", lambda s: None)
    tab = FakeTurnstileTab(token=None)
    click_called = []

    def fake_click(t, log):
        click_called.append(True)
        t._token = "CLICKED_TOKEN"
        return True

    monkeypatch.setattr("cf_bypasser.core.turnstile.click_turnstile", fake_click)
    res = inject_and_solve_turnstile(
        tab,
        url="https://example.com/form",
        sitekey="0x4AAAAAAtest",
        timeout=5.0,
        poll_interval=0.01,
    )
    assert res.success is True
    assert res.token == "CLICKED_TOKEN"
    assert len(click_called) >= 1


# ---------------------------------------------------------------------------
# CFBypasser integration tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bypasser_get_turnstile_token_success(monkeypatch):
    bypasser = CFBypasser(log=False, cache_enabled=False)
    
    async def fake_run(func, *args):
        return {
            "token": "MOCK_TOKEN",
            "user_agent": "MockUA/1.0",
            "elapsed_time": 1.23,
            "cookies": {},
        }
    
    class FakeSlot:
        browser = MagicMock()
        poisoned = False

    class FakeLease:
        async def __aenter__(self):
            return FakeSlot()
        async def __aexit__(self, *args):
            pass

    monkeypatch.setattr(bypasser.pool, "lease", lambda: FakeLease())
    monkeypatch.setattr(bypasser.pool, "run", fake_run)

    res = await bypasser.get_turnstile_token("https://example.com", "0x4AAAAAA")
    assert res is not None
    assert res["token"] == "MOCK_TOKEN"
    assert res["user_agent"] == "MockUA/1.0"
    assert res["elapsed_time"] == 1.23


@pytest.mark.asyncio
async def test_bypasser_get_turnstile_token_invalid_proxy():
    bypasser = CFBypasser(log=False)
    # Invalid proxy scheme should fail gracefully and return None
    res = await bypasser.get_turnstile_token("https://example.com", "0x4AAAAAA", proxy="ftp://bad-proxy:8080")
    assert res is None


@pytest.mark.asyncio
async def test_bypasser_get_turnstile_token_failure(monkeypatch):
    bypasser = CFBypasser(log=False)

    async def fake_run(func, *args):
        return None

    class FakeSlot:
        browser = MagicMock()
        poisoned = False

    class FakeLease:
        async def __aenter__(self):
            return FakeSlot()
        async def __aexit__(self, *args):
            pass

    monkeypatch.setattr(bypasser.pool, "lease", lambda: FakeLease())
    monkeypatch.setattr(bypasser.pool, "run", fake_run)

    res = await bypasser.get_turnstile_token("https://example.com", "0x4AAAAAA")
    assert res is None


# ---------------------------------------------------------------------------
# FastAPI API tests
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client():
    app = create_app()
    with TestClient(app) as client:
        yield client


def test_turnstile_post_endpoint_success(api_client, monkeypatch):
    async def fake_token(self, url, sitekey, action=None, cdata=None, pagedata=None, proxy=None, timeout=None):
        return {
            "token": "API_TEST_TOKEN",
            "user_agent": "Mozilla/5.0 TestUA",
            "elapsed_time": 0.85,
            "cookies": {},
        }

    monkeypatch.setattr(CFBypasser, "get_turnstile_token", fake_token)
    payload = {
        "url": "https://example.com/login",
        "sitekey": "0x4AAAAAA_test",
        "action": "login",
        "cdata": "custom1",
    }
    resp = api_client.post("/turnstile", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["token"] == "API_TEST_TOKEN"
    assert data["user_agent"] == "Mozilla/5.0 TestUA"
    assert data["sitekey"] == "0x4AAAAAA_test"
    assert data["url"] == "https://example.com/login"
    assert data["elapsed_time"] == 0.85


def test_turnstile_get_endpoint_success(api_client, monkeypatch):
    async def fake_token(self, url, sitekey, action=None, cdata=None, pagedata=None, proxy=None, timeout=None):
        return {
            "token": "GET_TOKEN_SUCCESS",
            "user_agent": "Mozilla/5.0 TestUA",
            "elapsed_time": 1.12,
            "cookies": {},
        }

    monkeypatch.setattr(CFBypasser, "get_turnstile_token", fake_token)
    resp = api_client.get(
        "/turnstile",
        params={"url": "https://example.com/submit", "sitekey": "0x4AAAAAA_test", "action": "submit"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["token"] == "GET_TOKEN_SUCCESS"
    assert data["sitekey"] == "0x4AAAAAA_test"
    assert data["url"] == "https://example.com/submit"


def test_turnstile_rejects_unsafe_urls(api_client):
    # Localhost and private IPs must be rejected
    resp = api_client.post("/turnstile", json={"url": "http://127.0.0.1/login", "sitekey": "0x4AAAA"})
    assert resp.status_code == 400
    assert "Invalid or unsafe URL" in resp.json()["detail"]

    resp = api_client.get("/turnstile", params={"url": "http://localhost/test", "sitekey": "0x4AAAA"})
    assert resp.status_code == 400
    assert "Invalid or unsafe URL" in resp.json()["detail"]


def test_turnstile_validation_missing_params(api_client):
    # Missing sitekey
    resp = api_client.post("/turnstile", json={"url": "https://example.com"})
    assert resp.status_code == 422

    # Empty sitekey
    resp = api_client.post("/turnstile", json={"url": "https://example.com", "sitekey": "   "})
    assert resp.status_code == 422

    # GET without required params
    resp = api_client.get("/turnstile", params={"url": "https://example.com"})
    assert resp.status_code == 400
    assert "sitekey" in resp.json()["detail"]

    # Invalid proxy format
    resp = api_client.post(
        "/turnstile",
        json={"url": "https://example.com", "sitekey": "0x4AAAA", "proxy": "invalid-proxy"},
    )
    assert resp.status_code == 422


def test_turnstile_failure_returns_500(api_client, monkeypatch):
    async def fake_fail(self, *args, **kwargs):
        return None

    monkeypatch.setattr(CFBypasser, "get_turnstile_token", fake_fail)
    resp = api_client.post(
        "/turnstile",
        json={"url": "https://example.com", "sitekey": "0x4AAAA"},
    )
    assert resp.status_code == 500
    assert "Failed to solve Cloudflare Turnstile challenge" in resp.json()["detail"]


def test_turnstile_with_x_hostname_is_mirrored(api_client, monkeypatch):
    from cf_bypasser.core.mirror import RequestMirror

    async def fake_mirror(self, **kw):
        return 200, {"content-type": "application/json"}, b'{"mirrored": true}'

    monkeypatch.setattr(RequestMirror, "mirror_request", fake_mirror)
    resp = api_client.get(
        "/turnstile",
        headers={"x-hostname": "example.com"},
        params={"url": "https://example.com", "sitekey": "0x4AAAA"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"mirrored": True}


# ---------------------------------------------------------------------------
# Live tests with runtime Brave browser (official Cloudflare test sitekeys)
# ---------------------------------------------------------------------------

@pytest.mark.live
def test_live_turnstile_always_passes_key():
    from cf_bypasser.browser.pool import launch_chromium
    from cf_bypasser.browser.context import BrowserContextSession

    browser = launch_chromium(headless=True)
    try:
        with BrowserContextSession(browser) as session:
            # Cloudflare's official dummy test sitekey for visible always-passing widget
            res = inject_and_solve_turnstile(
                session.tab,
                url="https://example.com",
                sitekey="1x00000000000000000000AA",
                timeout=20.0,
            )
            assert res.success is True
            assert res.token is not None
            assert len(res.token) > 0
    finally:
        browser.quit()


@pytest.mark.live
def test_live_turnstile_interactive_key():
    from cf_bypasser.browser.pool import launch_chromium
    from cf_bypasser.browser.context import BrowserContextSession

    browser = launch_chromium(headless=True)
    try:
        with BrowserContextSession(browser) as session:
            # Cloudflare's official dummy test sitekey that forces interaction / checkbox click
            res = inject_and_solve_turnstile(
                session.tab,
                url="https://example.com",
                sitekey="3x00000000000000000000FF",
                timeout=20.0,
            )
            assert res.success is True
            assert res.token is not None
            assert len(res.token) > 0
    finally:
        browser.quit()


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_turnstile_actual_page_vercel():
    from curl_cffi import requests
    bypasser = CFBypasser()
    await bypasser.start()
    try:
        url = "https://turnstile-test.vercel.app/"
        sitekey = "0x4AAAAAAAA1WzHSsbGWTH88"
        res = await bypasser.get_turnstile_token(url=url, sitekey=sitekey, timeout=30.0)
        assert res is not None, "Failed to solve Turnstile for vercel test page"
        assert res.get("token"), "Empty token returned"

        # Submit the token to the real vercel test backend which calls Cloudflare /siteverify
        resp = requests.post(
            url,
            data={"name": "Antigravity Live Test", "cf-turnstile-response": res["token"]},
            headers={"User-Agent": res["user_agent"], "Referer": url},
            impersonate="chrome",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("success") is True, f"Turnstile token rejected by server: {body}"
    finally:
        await bypasser.cleanup()
