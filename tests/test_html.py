import pytest
import asyncio


@pytest.mark.asyncio
async def test_single_html_retrieval(bypasser, test_url, expected_text):
    """Test basic HTML content retrieval."""
    result = await bypasser.get_or_generate_html(test_url)
    
    assert result is not None, "Failed to retrieve HTML content"
    assert "html" in result, "Result missing 'html' key"
    assert "cookies" in result, "Result missing 'cookies' key"
    assert "user_agent" in result, "Result missing 'user_agent' key"
    assert "url" in result, "Result missing 'url' key"
    
    html_content = result["html"]
    assert html_content, "HTML content is empty"
    assert len(html_content) > 50, f"HTML content too short: {len(html_content)} chars"
    assert expected_text in html_content, f"Expected text '{expected_text}' not found in HTML"
    
    cookies = result["cookies"]
    assert len(cookies) > 0, "No cookies in result"
    
    cf_cookies = [name for name in cookies.keys() if name.startswith(('cf_', '__cf'))]
    assert len(cf_cookies) > 0, f"No Cloudflare cookies found"
    
    user_agent = result["user_agent"]
    assert user_agent, "User agent is empty"
    assert "Mozilla" in user_agent, f"Invalid user agent: {user_agent}"
    
    assert result["url"], "URL is empty"
    assert test_url in result["url"], f"URL mismatch: expected {test_url}, got {result['url']}"
    
    print(f"Successfully retrieved HTML content: {len(html_content)} chars, {len(cookies)} cookies")


@pytest.mark.asyncio
async def test_html_content_validation(bypasser, test_url, expected_text):
    """Test that HTML content contains expected elements."""
    result = await bypasser.get_or_generate_html(test_url)
    assert result is not None, "Failed to retrieve HTML content"
    
    html_content = result["html"]
    assert "<html" in html_content.lower() or "<!doctype" in html_content.lower(), "Invalid HTML structure"
    assert expected_text in html_content, f"Success text not found in HTML"


@pytest.mark.asyncio
async def test_parallel_html_retrieval_3(bypasser, test_url, expected_text):
    """Test parallel HTML retrieval with 3 concurrent requests."""
    tasks = [bypasser.get_or_generate_html(test_url) for _ in range(3)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successful = 0
    for i, result in enumerate(results, 1):
        if isinstance(result, Exception):
            print(f"Request {i} failed: {result}")
        else:
            assert result is not None, f"Request {i} returned None"
            assert "html" in result, f"Request {i} missing html"
            assert expected_text in result["html"], f"Request {i} - success text not found"
            successful += 1
    
    assert successful == 3, f"Only {successful}/3 requests succeeded"


@pytest.mark.asyncio
async def test_parallel_html_retrieval_6(bypasser, test_url, expected_text):
    """Test parallel HTML retrieval with 6 concurrent requests."""
    tasks = [bypasser.get_or_generate_html(test_url) for _ in range(6)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successful = 0
    for i, result in enumerate(results, 1):
        if isinstance(result, Exception):
            print(f"Request {i} failed: {result}")
        else:
            assert result is not None, f"Request {i} returned None"
            assert "html" in result, f"Request {i} missing html"
            assert expected_text in result["html"], f"Request {i} - success text not found"
            successful += 1
    
    assert successful == 6, f"Only {successful}/6 requests succeeded"


@pytest.mark.asyncio
async def test_html_fresh_content(bypasser, test_url, expected_text):
    """Test that HTML endpoint always returns fresh content (not cached HTML)."""
    result1 = await bypasser.get_or_generate_html(test_url)
    assert result1 is not None, "First request failed"
    html1 = result1["html"]
    
    result2 = await bypasser.get_or_generate_html(test_url)
    assert result2 is not None, "Second request failed"
    html2 = result2["html"]
    
    assert expected_text in html1, "First request - success text not found"
    assert expected_text in html2, "Second request - success text not found"
