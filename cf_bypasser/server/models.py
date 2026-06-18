from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, HttpUrl, field_validator


class CookieRequest(BaseModel):
    url: HttpUrl = Field(..., description="Target URL to get cookies for")
    retries: int = Field(5, ge=1, le=10, description="Number of retry attempts")
    proxy: Optional[str] = Field(None, description="Proxy URL (optional)")

    @field_validator('proxy')
    @classmethod
    def validate_proxy(cls, v):
        if v and not v.startswith(('http://', 'https://', 'socks4://', 'socks5://')):
            raise ValueError('Proxy must start with http://, https://, socks4://, or socks5://')
        return v


class CookieResponse(BaseModel):
    cookies: Dict[str, str] = Field(..., description="Generated cookies")
    user_agent: str = Field(..., description="User agent used for cookie generation")


class MirrorRequestHeaders(BaseModel):
    x_hostname: str = Field(..., alias="x-hostname", description="Target hostname")
    x_proxy: Optional[str] = Field(None, alias="x-proxy", description="Proxy URL (optional)")
    x_bypass_cache: Optional[bool] = Field(False, alias="x-bypass-cache", description="Bypass cookie cache")

    @field_validator('x_proxy')
    @classmethod
    def validate_proxy(cls, v):
        if v and not v.startswith(('http://', 'https://', 'socks4://', 'socks5://')):
            raise ValueError('Proxy must start with http://, https://, socks4://, or socks5://')
        return v

    @field_validator('x_hostname')
    @classmethod
    def validate_hostname(cls, v):
        if not v or v.strip() == '':
            raise ValueError('x-hostname cannot be empty')
        return v.strip()


class MirrorResponse(BaseModel):
    status_code: int = Field(..., description="HTTP status code from target")
    headers: Dict[str, str] = Field(..., description="Response headers from target")
    content_length: int = Field(..., description="Length of response content")
    content_type: Optional[str] = Field(None, description="Content type of response")


class CacheStatsResponse(BaseModel):
    cached_entries: int = Field(..., description="Number of active cached entries")
    total_hostnames: int = Field(..., description="Total number of hostnames in cache")
    hostnames: List[str] = Field(..., description="List of cached hostnames")


class CacheClearResponse(BaseModel):
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Operation message")


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    timestamp: Optional[str] = Field(None, description="Error timestamp")


class MirrorRequestInfo(BaseModel):
    method: str = Field(..., description="HTTP method")
    hostname: str = Field(..., description="Target hostname")
    path: str = Field(..., description="Request path")
    proxy_used: Optional[str] = Field(None, description="Proxy used (if any)")
    cache_bypassed: bool = Field(False, description="Whether cache was bypassed")
    attempt_number: int = Field(1, description="Attempt number")
    max_attempts: int = Field(3, description="Maximum attempts")


class CookieGenerationInfo(BaseModel):
    hostname: str = Field(..., description="Target hostname")
    cache_hit: bool = Field(..., description="Whether cookies were found in cache")
    generation_time_ms: Optional[int] = Field(None, description="Time taken to generate cookies (ms)")
    user_agent: str = Field(..., description="User agent used")
    cookie_count: int = Field(..., description="Number of cookies generated")
    cf_cookies: List[str] = Field(..., description="List of Cloudflare-specific cookie names")


class ProxyInfo(BaseModel):
    proxy_url: str = Field(..., description="Proxy URL")
    proxy_type: str = Field(..., description="Proxy type (http, https, socks4, socks5)")
    has_auth: bool = Field(..., description="Whether proxy has authentication")

    @field_validator('proxy_type')
    @classmethod
    def validate_proxy_type(cls, v):
        allowed_types = ['http', 'https', 'socks4', 'socks5']
        if v not in allowed_types:
            raise ValueError(f'Proxy type must be one of: {allowed_types}')
        return v


class BypassAttemptResult(BaseModel):
    success: bool = Field(..., description="Whether bypass was successful")
    attempt_number: int = Field(..., description="Attempt number")
    challenge_type: Optional[str] = Field(None, description="Type of challenge encountered")
    time_taken_ms: int = Field(..., description="Time taken for this attempt")
    error_message: Optional[str] = Field(None, description="Error message if failed")
