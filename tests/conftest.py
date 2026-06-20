import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

TEST_URL = "https://challenge.sarper.me"
EXPECTED_SUCCESS_TEXT = "cloudflare challenged passed. You are now a free bot."
SERVER_URL = "http://localhost:8000"
CF_COOKIE_PREFIXES = ("cf_", "__cf")
MIN_HTML_LENGTH = 50


@pytest.fixture
def test_url():
    """Provide the test URL with Cloudflare challenge."""
    return TEST_URL


@pytest.fixture
def expected_text():
    """Provide the expected success text after bypass."""
    return EXPECTED_SUCCESS_TEXT


@pytest.fixture
def server_url():
    """Provide the running server URL for live/network tests."""
    return SERVER_URL


@pytest.fixture
def cf_cookie_prefixes():
    """Cookie-name prefixes that mark a Cloudflare clearance cookie."""
    return CF_COOKIE_PREFIXES


@pytest.fixture
def min_html_length():
    """Minimum plausible length for a real bypassed HTML body."""
    return MIN_HTML_LENGTH


@pytest.fixture
def client():
    """FastAPI TestClient against a freshly created app (runs lifespan so the singletons exist)."""
    from cf_bypasser.server.app import create_app
    with TestClient(create_app()) as c:
        yield c


@pytest_asyncio.fixture
async def bypasser():
    """Create a CloakBypasser instance for testing."""
    from cf_bypasser.core.bypasser import CloakBypasser
    instance = CloakBypasser(max_retries=5, log=True)
    yield instance
    await instance.cleanup()


# One real cookie-gen / HTML fetch shared across the whole session so the live
# suite launches a browser once instead of per test.
@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def shared_cookies():
    from cf_bypasser.core.bypasser import CloakBypasser
    instance = CloakBypasser(max_retries=5, log=True)
    try:
        return await instance.get_or_generate_cookies(TEST_URL)
    finally:
        await instance.cleanup()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def shared_html():
    from cf_bypasser.core.bypasser import CloakBypasser
    instance = CloakBypasser(max_retries=5, log=True)
    try:
        return await instance.get_or_generate_html(TEST_URL)
    finally:
        await instance.cleanup()
