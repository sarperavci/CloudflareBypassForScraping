import pytest
import asyncio

pytestmark = pytest.mark.live


@pytest.mark.asyncio
async def test_single_html_retrieval(shared_html, test_url, expected_text, cf_cookie_prefixes, min_html_length):
    """Test basic HTML content retrieval."""
    result = shared_html

    assert result is not None, "Failed to retrieve HTML content"
    assert "html" in result, "Result missing 'html' key"
    assert "cookies" in result, "Result missing 'cookies' key"
    assert "user_agent" in result, "Result missing 'user_agent' key"
    assert "url" in result, "Result missing 'url' key"

    html_content = result["html"]
    assert html_content, "HTML content is empty"
    assert len(html_content) > min_html_length, f"HTML content too short: {len(html_content)} chars"
    assert expected_text in html_content, f"Expected text '{expected_text}' not found in HTML"

    cookies = result["cookies"]
    assert len(cookies) > 0, "No cookies in result"

    cf_cookies = [name for name in cookies.keys() if name.startswith(cf_cookie_prefixes)]
    assert len(cf_cookies) > 0, "No Cloudflare cookies found"

    user_agent = result["user_agent"]
    assert user_agent and "Mozilla" in user_agent, f"Invalid user agent: {user_agent}"

    assert result["url"], "URL is empty"
    assert test_url in result["url"], f"URL mismatch: expected {test_url}, got {result['url']}"


@pytest.mark.asyncio
async def test_html_content_validation(shared_html, expected_text):
    """Test that HTML content contains expected elements."""
    result = shared_html
    assert result is not None, "Failed to retrieve HTML content"

    html_content = result["html"]
    assert "<html" in html_content.lower() or "<!doctype" in html_content.lower(), "Invalid HTML structure"
    assert expected_text in html_content, "Success text not found in HTML"


@pytest.mark.parametrize("n", [3])
@pytest.mark.asyncio
async def test_parallel_html_retrieval(bypasser, test_url, expected_text, n):
    """The live concurrency test: concurrent HTML fetches run in parallel (semaphore-bounded)."""
    tasks = [bypasser.get_or_generate_html(test_url) for _ in range(n)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, result in enumerate(results, 1):
        assert not isinstance(result, Exception), f"Request {i} failed: {result!r}"
        assert result is not None, f"Request {i} returned None"
        assert expected_text in result["html"], f"Request {i} - success text not found"


@pytest.mark.asyncio
async def test_html_fresh_content(bypasser, test_url, expected_text):
    """The /html endpoint fetches fresh content even when bypassing the cookie cache."""
    result = await bypasser.get_or_generate_html(test_url, bypass_cache=True)
    assert result is not None, "Fresh request failed"
    assert expected_text in result["html"], "Success text not found in fresh HTML"
