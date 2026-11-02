from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

from cf_bypasser.utils.constants import PROXY_SCHEMES


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
        if v and not v.startswith(PROXY_SCHEMES):
            raise ValueError('Proxy must start with http://, https://, socks4://, or socks5://')
        return v

    @field_validator('x_hostname')
    @classmethod
    def validate_hostname(cls, v):
        if not v or v.strip() == '':
            raise ValueError('x-hostname cannot be empty')
        return v.strip()


class CacheStatsResponse(BaseModel):
    cached_entries: int = Field(..., description="Number of active cached entries")
    total_hostnames: int = Field(..., description="Total number of hostnames in cache")
    hostnames: List[str] = Field(..., description="List of cached hostnames")


class CacheClearResponse(BaseModel):
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Operation message")


class BrowserInfo(BaseModel):
    index: int = Field(..., description="Browser slot index")
    state: str = Field(..., description="idle, busy or restarting")
    jobs: int = Field(..., description="Jobs served since the last (re)launch")
    pid: Optional[int] = Field(None, description="Browser process id (null while restarting)")


class BrowserPoolResponse(BaseModel):
    total: int = Field(..., description="Configured number of browsers")
    available: int = Field(..., description="Idle browsers ready for a request")
    busy: int = Field(..., description="Browsers currently serving a request")
    restarting: int = Field(..., description="Browsers being relaunched")
    browsers: List[BrowserInfo] = Field(..., description="Per-browser state")


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    timestamp: Optional[str] = Field(None, description="Error timestamp")


class TurnstileRequest(BaseModel):
    url: str = Field(..., description="Target webpage URL where Turnstile is verified")
    sitekey: str = Field(..., description="Cloudflare Turnstile sitekey")
    action: Optional[str] = Field(None, description="Optional Turnstile action parameter")
    cdata: Optional[str] = Field(None, description="Optional Turnstile cData parameter")
    pagedata: Optional[str] = Field(None, description="Optional Turnstile chlPageData parameter")
    proxy: Optional[str] = Field(None, description="Proxy URL (optional)")

    @field_validator('proxy')
    @classmethod
    def validate_proxy(cls, v):
        if v and not v.startswith(PROXY_SCHEMES):
            raise ValueError('Proxy must start with http://, https://, socks4://, or socks5://')
        return v

    @field_validator('sitekey')
    @classmethod
    def validate_sitekey(cls, v):
        if not v or not v.strip():
            raise ValueError('sitekey cannot be empty')
        return v.strip()

    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        if not v or not v.strip():
            raise ValueError('url cannot be empty')
        return v.strip()


class TurnstileResponse(BaseModel):
    token: str = Field(..., description="Generated Turnstile clearance token")
    user_agent: str = Field(..., description="User agent of the browser that solved the widget")
    elapsed_time: float = Field(..., description="Time taken to solve Turnstile in seconds")
    sitekey: str = Field(..., description="Sitekey solved")
    url: str = Field(..., description="Target URL")
