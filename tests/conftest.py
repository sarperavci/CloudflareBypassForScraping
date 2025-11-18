import pytest
import asyncio
from typing import AsyncGenerator

# Test configuration
TEST_URL = "https://challenge.sarper.me"
EXPECTED_SUCCESS_TEXT = "cloudflare challenged passed. You are now a free bot."
TEST_TIMEOUT = 60  # seconds per test


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_url():
    """Provide the test URL with Cloudflare challenge."""
    return TEST_URL


@pytest.fixture
def expected_text():
    """Provide the expected success text after bypass."""
    return EXPECTED_SUCCESS_TEXT


@pytest.fixture
async def bypasser():
    """Create a CamoufoxBypasser instance for testing."""
    from cf_bypasser.core.bypasser import CamoufoxBypasser
    instance = CamoufoxBypasser(max_retries=5, log=True)
    yield instance
    # Cleanup is handled per-request now, but just in case
    await instance.cleanup()
