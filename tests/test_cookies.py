import pytest
import asyncio


@pytest.mark.asyncio
async def test_single_cookie_generation(shared_cookies):
    """Test basic cookie generation for a single request."""
    result = shared_cookies

    assert result is not None, "Failed to generate cookies"
    assert "cookies" in result, "Result missing 'cookies' key"
    assert "user_agent" in result, "Result missing 'user_agent' key"

    cookies = result["cookies"]
    assert len(cookies) > 0, "No cookies generated"

    cf_cookies = [name for name in cookies.keys() if name.startswith(('cf_', '__cf'))]
    assert len(cf_cookies) > 0, f"No Cloudflare cookies found. Got: {list(cookies.keys())}"

    user_agent = result["user_agent"]
    assert user_agent, "User agent is empty"
    assert "Mozilla" in user_agent, f"Invalid user agent: {user_agent}"


@pytest.mark.asyncio
async def test_cookie_caching(bypasser, test_url):
    """Test that cookies are properly cached and reused."""
    result1 = await bypasser.get_or_generate_cookies(test_url)
    assert result1 is not None, "First request failed"

    result2 = await bypasser.get_or_generate_cookies(test_url)
    assert result2 is not None, "Second request failed"

    assert result1["cookies"] == result2["cookies"], "Cookies don't match - caching failed"
    assert result1["user_agent"] == result2["user_agent"], "User agents don't match - caching failed"


@pytest.mark.asyncio
async def test_cookie_validation(shared_cookies):
    """Test that generated cookies have valid structure."""
    result = shared_cookies
    assert result is not None, "Failed to generate cookies"

    for name, value in result["cookies"].items():
        assert name, "Cookie name is empty"
        assert value, f"Cookie '{name}' has empty value"
        assert isinstance(name, str), f"Cookie name '{name}' is not a string"
        assert isinstance(value, str), f"Cookie value for '{name}' is not a string"


@pytest.mark.asyncio
async def test_parallel_cookie_generation_3(bypasser, test_url):
    """Concurrent cookie requests all succeed (in-flight dedup + cache)."""
    tasks = [bypasser.get_or_generate_cookies(test_url) for _ in range(3)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    successful = 0
    for i, result in enumerate(results, 1):
        if isinstance(result, Exception):
            print(f"Request {i} failed: {result}")
        else:
            assert result is not None, f"Request {i} returned None"
            assert len(result["cookies"]) > 0, f"Request {i} has no cookies"
            successful += 1

    assert successful == 3, f"Only {successful}/3 requests succeeded"
