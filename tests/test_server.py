import pytest
import asyncio
import httpx
from fastapi.testclient import TestClient


@pytest.fixture
def server_url():
    """Provide the server URL for testing."""
    return "http://localhost:8000"


@pytest.fixture
def client():
    """Create a test client for the FastAPI server."""
    from cf_bypasser.server.app import create_app
    app = create_app()
    return TestClient(app)


def test_cookies_endpoint_single(client, test_url, expected_text):
    """Test the /cookies endpoint with a single request."""
    response = client.get("/cookies", params={"url": test_url, "retries": 5})
    
    assert response.status_code == 200, f"Request failed with status {response.status_code}"
    data = response.json()
    
    assert "cookies" in data, "Response missing 'cookies'"
    assert "user_agent" in data, "Response missing 'user_agent'"
    
    cookies = data["cookies"]
    assert len(cookies) > 0, "No cookies returned"
    
    cf_cookies = [name for name in cookies.keys() if name.startswith(('cf_', '__cf'))]
    assert len(cf_cookies) > 0, f"No Cloudflare cookies found"


def test_html_endpoint_single(client, test_url, expected_text):
    """Test the /html endpoint with a single request."""
    response = client.get("/html", params={"url": test_url, "retries": 5})
    
    assert response.status_code == 200, f"Request failed with status {response.status_code}"
    html_content = response.text
    
    assert html_content, "HTML content is empty"
    assert len(html_content) > 50, f"HTML content too short: {len(html_content)} chars"
    assert expected_text in html_content, f"Success text not found in HTML"
    
    assert "x-cf-bypasser-cookies" in response.headers, "Missing x-cf-bypasser-cookies header"
    assert "x-cf-bypasser-user-agent" in response.headers, "Missing x-cf-bypasser-user-agent header"
    assert "x-processing-time-ms" in response.headers, "Missing x-processing-time-ms header"


def test_cookies_endpoint_invalid_url(client):
    """Test the /cookies endpoint with invalid URL."""
    response = client.get("/cookies", params={"url": "http://localhost:8080", "retries": 5})
    assert response.status_code == 400, "Should reject localhost URLs"


def test_html_endpoint_invalid_url(client):
    """Test the /html endpoint with invalid URL."""
    response = client.get("/html", params={"url": "http://192.168.1.1", "retries": 5})
    assert response.status_code == 400, "Should reject private IPs"


@pytest.mark.asyncio
async def test_cookies_endpoint_parallel_3(server_url, test_url):
    """Test /cookies endpoint with 3 parallel requests."""
    async with httpx.AsyncClient() as client:
        tasks = [
            client.get(f"{server_url}/cookies", params={"url": test_url, "retries": 5}, timeout=60.0)
            for _ in range(3)
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = 0
        for i, response in enumerate(responses, 1):
            if isinstance(response, Exception):
                print(f"Request {i} failed: {response}")
            else:
                assert response.status_code == 200, f"Request {i} failed with status {response.status_code}"
                data = response.json()
                assert "cookies" in data, f"Request {i} missing cookies"
                successful += 1
        
        assert successful == 3, f"Only {successful}/3 requests succeeded"


@pytest.mark.asyncio
async def test_html_endpoint_parallel_3(server_url, test_url, expected_text):
    """Test /html endpoint with 3 parallel requests."""
    async with httpx.AsyncClient() as client:
        tasks = [
            client.get(f"{server_url}/html", params={"url": test_url, "retries": 5}, timeout=60.0)
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
async def test_cache_stats_endpoint(server_url):
    """Test the /cache/stats endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{server_url}/cache/stats")
        
        assert response.status_code == 200, f"Request failed with status {response.status_code}"
        
        data = response.json()
        assert "cached_entries" in data, "Missing cached_entries"
        assert "total_hostnames" in data, "Missing total_hostnames"
        assert "hostnames" in data, "Missing hostnames"


@pytest.mark.asyncio
async def test_cache_clear_endpoint(server_url):
    """Test the /cache/clear endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{server_url}/cache/clear")
        
        assert response.status_code == 200, f"Request failed with status {response.status_code}"
        
        data = response.json()
        assert "status" in data, "Missing status"
        assert data["status"] == "success", f"Status is not success: {data['status']}"
