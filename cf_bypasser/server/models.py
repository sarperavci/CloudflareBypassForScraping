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


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    timestamp: Optional[str] = Field(None, description="Error timestamp")
