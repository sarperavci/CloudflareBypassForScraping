import pytest
import asyncio
import httpx


@pytest.fixture
def server_url():
    """Provide the server URL for testing."""
    return "http://localhost:8000"


@pytest.mark.asyncio
async def test_mirror_get_request(server_url, expected_text):
    """Test mirroring a simple GET request."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{server_url}/",
            headers={"x-hostname": "challenge.sarper.me"},
            timeout=60.0
        )
        
        assert response.status_code == 200, f"Request failed with status {response.status_code}"
        html_content = response.text
        assert expected_text in html_content, f"Success text not found in response"
        assert "x-cf-bypasser-version" in response.headers, "Missing x-cf-bypasser-version header"
        assert "x-processing-time-ms" in response.headers, "Missing x-processing-time-ms header"


@pytest.mark.asyncio
async def test_mirror_get_with_path(server_url):
    """Test mirroring a GET request with a path."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{server_url}/test-path",
            headers={"x-hostname": "challenge.sarper.me"},
            timeout=60.0
        )
        
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"


@pytest.mark.asyncio
async def test_mirror_missing_hostname(server_url):
    """Test mirror request without required x-hostname header."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{server_url}/test", timeout=10.0)
        assert response.status_code == 400, "Should reject requests without x-hostname"


@pytest.mark.asyncio
async def test_mirror_invalid_hostname(server_url):
    """Test mirror request with invalid hostname."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{server_url}/test",
            headers={"x-hostname": "localhost"},
            timeout=10.0
        )
        
        assert response.status_code == 400, "Should reject localhost hostnames"


@pytest.mark.asyncio
async def test_mirror_with_query_params(server_url):
    """Test mirroring a request with query parameters."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{server_url}/?param1=value1&param2=value2",
            headers={"x-hostname": "challenge.sarper.me"},
            timeout=60.0
        )
        
        assert response.status_code == 200, f"Request failed with status {response.status_code}"


@pytest.mark.asyncio
async def test_mirror_parallel_requests_3(server_url, expected_text):
    """Test 3 parallel mirror requests."""
    async with httpx.AsyncClient() as client:
        tasks = [
            client.get(
                f"{server_url}/",
                headers={"x-hostname": "challenge.sarper.me"},
                timeout=60.0
            )
            for _ in range(3)
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = 0
        for i, response in enumerate(responses, 1):
            if isinstance(response, Exception):
                print(f"Request {i} failed: {response}")
            else:
                assert response.status_code == 200, f"Request {i} failed with status {response.status_code}"
                assert expected_text in response.text, f"Request {i} - success text not found"
                successful += 1
        
        assert successful == 3, f"Only {successful}/3 requests succeeded"


@pytest.mark.asyncio
async def test_mirror_parallel_requests_6(server_url, expected_text):
    """Test 6 parallel mirror requests."""
    async with httpx.AsyncClient() as client:
        tasks = [
            client.get(
                f"{server_url}/",
                headers={"x-hostname": "challenge.sarper.me"},
                timeout=60.0
            )
            for _ in range(6)
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = 0
        for i, response in enumerate(responses, 1):
            if isinstance(response, Exception):
                print(f"Request {i} failed: {response}")
            else:
                assert response.status_code == 200, f"Request {i} failed with status {response.status_code}"
                assert expected_text in response.text, f"Request {i} - success text not found"
                successful += 1
        
        assert successful == 6, f"Only {successful}/6 requests succeeded"


@pytest.mark.asyncio
async def test_mirror_different_methods(server_url):
    """Test mirror with different HTTP methods."""
    async with httpx.AsyncClient() as client:
        response_get = await client.get(
            f"{server_url}/api/test",
            headers={"x-hostname": "challenge.sarper.me"},
            timeout=60.0
        )
        
        response_post = await client.post(
            f"{server_url}/api/test",
            headers={"x-hostname": "challenge.sarper.me"},
            json={"test": "data"},
            timeout=60.0
        )
        
        assert response_get.status_code in [200, 404, 405], "GET failed"
        assert response_post.status_code in [200, 404, 405], "POST failed"


@pytest.mark.asyncio
async def test_mirror_custom_headers(server_url, expected_text):
    """Test mirror with custom request headers."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{server_url}/",
            headers={
                "x-hostname": "challenge.sarper.me",
                "user-agent": "CustomBot/1.0",
                "accept-language": "en-US",
                "custom-header": "custom-value"
            },
            timeout=60.0
        )
        
        assert response.status_code == 200, f"Request failed with status {response.status_code}"
        assert expected_text in response.text, "Success text not found"


@pytest.mark.asyncio
async def test_mirror_cache_header(server_url, expected_text):
    """Test mirror with x-bypass-cache header."""
    async with httpx.AsyncClient() as client:
        response1 = await client.get(
            f"{server_url}/",
            headers={"x-hostname": "challenge.sarper.me"},
            timeout=60.0
        )
        assert response1.status_code == 200, "First request failed"
        
        response2 = await client.get(
            f"{server_url}/",
            headers={
                "x-hostname": "challenge.sarper.me",
                "x-bypass-cache": "true"
            },
            timeout=60.0
        )
        assert response2.status_code == 200, "Second request failed"
        assert "x-cache-bypassed" in response2.headers, "Missing cache-bypassed header"
