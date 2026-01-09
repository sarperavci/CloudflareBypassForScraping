import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture
def client():
    """Create a test client for the FastAPI server."""
    from cf_bypasser.server.app import create_app
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_bypasser():
    """Mock the CamoufoxBypasser for testing."""
    mock_instance = MagicMock()
    mock_instance.get_or_generate_cookies = AsyncMock(return_value={
        'cookies': {'cf_clearance': 'test_token_123', 'session': 'abc'},
        'user_agent': 'Mozilla/5.0 (Test)'
    })
    mock_instance.get_or_generate_html = AsyncMock(return_value={
        'cookies': {'cf_clearance': 'test_token_123'},
        'user_agent': 'Mozilla/5.0 (Test)',
        'html': '<html><body>Test HTML</body></html>',
        'url': 'https://example.com'
    })
    
    with patch('cf_bypasser.server.routes.global_bypasser', mock_instance):
        yield mock_instance


@pytest.fixture
def mock_mirror():
    """Mock the RequestMirror for testing."""
    mock_instance = MagicMock()
    mock_instance.mirror_request = AsyncMock(return_value=(
        200,
        {'content-type': 'application/json'},
        b'{"target_data": "from_target_cookies_endpoint"}'
    ))
    
    with patch('cf_bypasser.server.routes.global_mirror', mock_instance):
        yield mock_instance


class TestCookiesEndpoint:
    """Test /cookies endpoint behavior with and without x-hostname header."""
    
    def test_cookies_internal_api_without_x_hostname(self, client, mock_bypasser):
        """Test that /cookies works as internal API when x-hostname is NOT present (backward compatibility)."""
        response = client.get(
            "/cookies",
            params={"url": "https://example.com", "retries": 5}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Should return the internal API format
        assert "cookies" in data, "Response should contain 'cookies'"
        assert "user_agent" in data, "Response should contain 'user_agent'"
        assert data["cookies"]["cf_clearance"] == "test_token_123"
        assert "Mozilla" in data["user_agent"]
    
    def test_cookies_mirror_with_x_hostname(self, client, mock_mirror):
        """Test that /cookies forwards to mirror handler when x-hostname IS present."""
        response = client.get(
            "/cookies",
            headers={"x-hostname": "target-site.com"}
        )
        
        # Should forward to mirror handler and return target site's response
        assert response.status_code == 200
        data = response.json()
        
        # Should return the mirrored response from target site
        assert "target_data" in data
        assert data["target_data"] == "from_target_cookies_endpoint"
    
    def test_cookies_mirror_with_query_params(self, client, mock_mirror):
        """Test that /cookies with x-hostname preserves query parameters."""
        response = client.get(
            "/cookies?session_id=123&format=json",
            headers={"x-hostname": "api.target-site.com"}
        )
        
        assert response.status_code == 200
        # Verify mirror was called
        assert mock_mirror.mirror_request.called
    
    def test_cookies_invalid_url_without_x_hostname(self, client):
        """Test that /cookies rejects invalid URLs when used as internal API."""
        response = client.get(
            "/cookies",
            params={"url": "http://localhost:8080"}
        )
        
        assert response.status_code == 400
        assert "unsafe" in response.json()["detail"].lower() or "localhost" in response.json()["detail"].lower()


class TestHtmlEndpoint:
    """Test /html endpoint behavior with and without x-hostname header."""
    
    def test_html_internal_api_without_x_hostname(self, client, mock_bypasser):
        """Test that /html works as internal API when x-hostname is NOT present (backward compatibility)."""
        response = client.get(
            "/html",
            params={"url": "https://example.com", "retries": 5}
        )
        
        assert response.status_code == 200
        
        # Should return raw HTML content
        assert "Test HTML" in response.text
        
        # Check custom headers from internal API
        assert "x-cf-bypasser-cookies" in response.headers
        assert "x-cf-bypasser-user-agent" in response.headers
        assert "x-processing-time-ms" in response.headers
    
    def test_html_mirror_with_x_hostname(self, client, mock_mirror):
        """Test that /html forwards to mirror handler when x-hostname IS present."""
        response = client.get(
            "/html",
            headers={"x-hostname": "target-site.com"}
        )
        
        # Should forward to mirror handler
        assert response.status_code == 200
        data = response.json()
        
        # Should return the mirrored response from target site
        assert "target_data" in data
        assert data["target_data"] == "from_target_cookies_endpoint"
    
    def test_html_mirror_with_bypass_cache(self, client, mock_mirror):
        """Test that /html with x-hostname and x-bypass-cache both headers work together."""
        response = client.get(
            "/html",
            headers={
                "x-hostname": "target-site.com",
                "x-bypass-cache": "true"
            }
        )
        
        assert response.status_code == 200
        # Verify mirror was called
        assert mock_mirror.mirror_request.called
    
    def test_html_invalid_url_without_x_hostname(self, client):
        """Test that /html rejects invalid URLs when used as internal API."""
        response = client.get(
            "/html",
            params={"url": "http://192.168.1.1"}
        )
        
        assert response.status_code == 400
        assert "unsafe" in response.json()["detail"].lower() or "private" in response.json()["detail"].lower()


class TestCollisionScenarios:
    """Test specific collision scenarios mentioned in issue #113."""
    
    def test_target_site_cookies_path_with_mirror(self, client, mock_mirror):
        """Test mirroring a request to https://target-site.com/cookies."""
        # This is the exact scenario from the issue
        response = client.get(
            "/cookies",
            headers={"x-hostname": "target-site.com"}
        )
        
        assert response.status_code == 200
        # Should NOT use internal API, should mirror to target site
        data = response.json()
        assert "target_data" in data, "Should return mirrored response, not internal API"
    
    def test_target_site_html_path_with_mirror(self, client, mock_mirror):
        """Test mirroring a request to https://target-site.com/html."""
        response = client.get(
            "/html",
            headers={"x-hostname": "target-site.com"}
        )
        
        assert response.status_code == 200
        # Should NOT use internal API, should mirror to target site
        data = response.json()
        assert "target_data" in data, "Should return mirrored response, not internal API"
    
    def test_complex_path_with_cookies_segment(self, client, mock_mirror):
        """Test that paths containing 'cookies' but not exactly '/cookies' work correctly."""
        mock_mirror.mirror_request = AsyncMock(return_value=(
            200,
            {'content-type': 'application/json'},
            b'{"data": "from_api_cookies_endpoint"}'
        ))
        
        response = client.get(
            "/api/cookies",
            headers={"x-hostname": "target-site.com"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == "from_api_cookies_endpoint"
    
    def test_post_request_to_cookies_path(self, client, mock_mirror):
        """Test POST request to /cookies path with x-hostname header."""
        mock_mirror.mirror_request = AsyncMock(return_value=(
            201,
            {'content-type': 'application/json'},
            b'{"created": true}'
        ))
        
        response = client.post(
            "/cookies",
            headers={
                "x-hostname": "api.target-site.com",
                "content-type": "application/json"
            },
            json={"key": "value"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["created"] is True


class TestMirrorRequestHeaders:
    """Test that mirror-specific headers work correctly."""
    
    def test_x_hostname_case_insensitive(self, client, mock_mirror):
        """Test that x-hostname header is case-insensitive."""
        # Test various cases
        for header_name in ["x-hostname", "X-Hostname", "X-HOSTNAME"]:
            response = client.get(
                "/cookies",
                headers={header_name: "target-site.com"}
            )
            assert response.status_code == 200
    
    def test_x_proxy_with_mirror_request(self, client, mock_mirror):
        """Test that x-proxy header is properly handled in mirror requests."""
        response = client.get(
            "/cookies",
            headers={
                "x-hostname": "target-site.com",
                "x-proxy": "http://proxy.example.com:8080"
            }
        )
        
        assert response.status_code == 200
    
    def test_all_mirror_headers_together(self, client, mock_mirror):
        """Test all mirror-specific headers working together."""
        response = client.post(
            "/html",
            headers={
                "x-hostname": "api.target-site.com",
                "x-proxy": "http://proxy.example.com:8080",
                "x-bypass-cache": "true",
                "content-type": "application/json"
            },
            json={"data": "test"}
        )
        
        assert response.status_code == 200


class TestBackwardCompatibility:
    """Test that existing integrations continue to work unchanged."""
    
    def test_legacy_cookies_endpoint_still_works(self, client, mock_bypasser):
        """Test that the legacy /cookies endpoint works exactly as before."""
        response = client.get(
            "/cookies",
            params={
                "url": "https://nopecha.com/demo/cloudflare",
                "retries": 5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "cookies" in data
        assert "user_agent" in data
    
    def test_legacy_html_endpoint_still_works(self, client, mock_bypasser):
        """Test that the legacy /html endpoint works exactly as before."""
        response = client.get(
            "/html",
            params={
                "url": "https://nopecha.com/demo/cloudflare",
                "retries": 5
            }
        )
        
        assert response.status_code == 200
        assert "Test HTML" in response.text
        assert "x-cf-bypasser-cookies" in response.headers
    
    def test_legacy_with_proxy_parameter(self, client, mock_bypasser):
        """Test that the legacy proxy parameter still works."""
        response = client.get(
            "/cookies",
            params={
                "url": "https://example.com",
                "proxy": "http://proxy.example.com:8080",
                "retries": 3
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "cookies" in data


class TestErrorHandling:
    """Test error handling in collision scenarios."""
    
    def test_missing_required_url_without_x_hostname(self, client):
        """Test that url parameter is required when x-hostname is not present."""
        response = client.get("/cookies")
        
        # Should return 400 with our custom error message for missing url
        assert response.status_code == 400
        data = response.json()
        assert "url parameter is required" in data["detail"].lower()
    
    def test_cache_paths_not_mirrorable(self, client):
        """Test that cache/ paths cannot be mirrored (reserved for internal use)."""
        response = client.get(
            "/cache/stats",
            headers={"x-hostname": "target-site.com"}
        )
        
        # cache/ paths should still be reserved for internal use
        # They should work as internal endpoints regardless of x-hostname
        assert response.status_code in [200, 500]  # Internal endpoint behavior


class TestEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_empty_x_hostname_header(self, client, mock_mirror):
        """Test behavior when x-hostname header is present but empty."""
        response = client.get(
            "/cookies",
            headers={"x-hostname": ""}
        )
        
        # Should be treated as mirror request, mirror handler should validate and reject empty hostname
        assert response.status_code in [400, 422]  # Either validation error is acceptable
    
    def test_multiple_headers_with_x_hostname(self, client, mock_mirror):
        """Test that custom headers are preserved when forwarding to mirror."""
        response = client.get(
            "/cookies",
            headers={
                "x-hostname": "api.target-site.com",
                "authorization": "Bearer token123",
                "x-custom-header": "custom-value"
            }
        )
        
        # Mirror should handle the request
        assert response.status_code == 200
    
    def test_different_http_methods_on_reserved_paths(self, client, mock_mirror):
        """Test various HTTP methods on /cookies and /html paths with x-hostname."""
        methods_responses = []
        
        # Test different methods
        for method, client_method in [
            ("GET", client.get),
            ("POST", client.post),
            ("PUT", client.put),
            ("DELETE", client.delete),
            ("PATCH", client.patch)
        ]:
            response = client_method(
                "/cookies",
                headers={"x-hostname": "api.target-site.com"}
            )
            methods_responses.append((method, response.status_code))
        
        # All should be handled by mirror (status 200)
        assert all(status == 200 for _, status in methods_responses), \
            f"Some methods failed: {methods_responses}"
