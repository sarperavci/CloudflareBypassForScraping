import logging
import time
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request, Response, Query, Depends

from cf_bypasser.core.bypasser import CloakBypasser
from cf_bypasser.core.mirror import RequestMirror
from cf_bypasser.server.models import (
    CookieResponse, CacheStatsResponse, CacheClearResponse, ErrorResponse,
)
from cf_bypasser.utils.constants import APP_VERSION, PROXY_SCHEMES, CF_COOKIE_PREFIXES
from cf_bypasser.utils.security import is_safe_url

global_bypasser = None
global_mirror = None

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Create the bypasser/mirror singletons on startup, clean them up on shutdown."""
    global global_bypasser, global_mirror

    logger.info("Starting Cloudflare Bypasser Server...")

    global_bypasser = CloakBypasser(max_retries=5, log=True)
    global_mirror = RequestMirror(global_bypasser)

    logger.info("Server initialization complete")

    yield

    logger.info("Shutting down Cloudflare Bypasser Server...")

    try:
        if global_mirror:
            await global_mirror.cleanup()

        if global_bypasser:
            await global_bypasser.cleanup()
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

    logger.info("Server shutdown complete")


def get_bypasser() -> CloakBypasser:
    """DI provider for the lifespan-created bypasser singleton."""
    return global_bypasser


def get_mirror() -> RequestMirror:
    """DI provider for the lifespan-created mirror singleton."""
    return global_mirror


def _validate_request(request: Request, url: Optional[str], proxy: Optional[str]) -> bool:
    """Validate a non-mirror request; returns True when x-hostname marks it as a mirror request."""
    if any(key.lower() == 'x-hostname' for key in request.headers.keys()):
        return True

    if not url:
        raise HTTPException(
            status_code=400,
            detail="url parameter is required when x-hostname header is not present"
        )

    if not is_safe_url(url):
        raise HTTPException(
            status_code=400,
            detail="Invalid or unsafe URL - localhost and private IPs are not allowed"
        )

    if proxy and not proxy.startswith(PROXY_SCHEMES):
        raise HTTPException(
            status_code=400,
            detail="Proxy must start with http://, https://, socks4://, or socks5://"
        )

    return False


def setup_routes(app: FastAPI):
    """Setup all routes for the FastAPI application."""

    @app.get("/cookies", response_model=CookieResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
    async def get_cookies(
        request: Request,
        url: Optional[str] = Query(None, description="Target URL to get cookies for"),
        retries: int = Query(5, ge=1, le=10, description="Number of retry attempts"),
        proxy: Optional[str] = Query(None, description="Proxy URL (optional)"),
        bypasser: CloakBypasser = Depends(get_bypasser),
    ):
        """Legacy endpoint: get Cloudflare clearance cookies, or mirror when x-hostname is present."""
        if _validate_request(request, url, proxy):
            return await mirror_request(request, "cookies", get_mirror())

        try:
            start_time = time.time()
            logger.info(f"Getting cookies for {url} (retries: {retries}, proxy: {'yes' if proxy else 'no'})")

            data = await bypasser.get_or_generate_cookies(url, proxy)

            if not data:
                raise HTTPException(status_code=500, detail="Failed to bypass Cloudflare protection")

            generation_time = int((time.time() - start_time) * 1000)
            cf_cookies = [name for name in data["cookies"].keys() if name.startswith(CF_COOKIE_PREFIXES)]

            logger.info(f"Successfully generated {len(data['cookies'])} cookies in {generation_time}ms")
            logger.info(f"Cloudflare cookies: {cf_cookies}")

            return CookieResponse(
                cookies=data["cookies"],
                user_agent=data["user_agent"]
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting cookies for {url}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @app.get("/html", responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
    async def get_html(
        request: Request,
        url: Optional[str] = Query(None, description="Target URL to get HTML content for"),
        retries: int = Query(5, ge=1, le=10, description="Number of retry attempts"),
        proxy: Optional[str] = Query(None, description="Proxy URL (optional)"),
        bypassCookieCache: bool = Query(False, description="Force fresh cookie generation"),
        bypasser: CloakBypasser = Depends(get_bypasser),
    ):
        """Get raw HTML from a URL after bypassing Cloudflare, or mirror when x-hostname is present."""
        if _validate_request(request, url, proxy):
            return await mirror_request(request, "html", get_mirror())

        try:
            start_time = time.time()
            logger.info(f"Getting HTML content for {url} (retries: {retries}, proxy: {'yes' if proxy else 'no'})")

            data = await bypasser.get_or_generate_html(url, proxy, bypass_cache=bypassCookieCache)

            if not data:
                raise HTTPException(status_code=500, detail="Failed to bypass Cloudflare protection")

            generation_time = int((time.time() - start_time) * 1000)
            cf_cookies = [name for name in data["cookies"].keys() if name.startswith(CF_COOKIE_PREFIXES)]
            content_length = len(data["html"])

            logger.info(f"Successfully generated HTML content ({content_length} chars) and {len(data['cookies'])} cookies in {generation_time}ms")
            logger.info(f"Cloudflare cookies: {cf_cookies}")

            return Response(
                content=data["html"],
                media_type="text/html",
                headers={
                    "x-cf-bypasser-cookies": str(len(data["cookies"])),
                    "x-cf-bypasser-user-agent": data["user_agent"],
                    "x-cf-bypasser-final-url": data["url"],
                    "x-processing-time-ms": str(generation_time)
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting HTML content for {url}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @app.post("/cache/clear", response_model=CacheClearResponse, responses={500: {"model": ErrorResponse}})
    async def clear_cache(
        bypasser: CloakBypasser = Depends(get_bypasser),
        mirror: RequestMirror = Depends(get_mirror),
    ):
        """Clear the cookie cache and cleanup active sessions."""
        try:
            cleared_entries = 0

            if bypasser:
                cache = bypasser.cookie_cache.cache
                cleared_entries = len(cache)
                bypasser.cookie_cache.clear_all()
                logger.info(f"Cleared {cleared_entries} cache entries")

            if mirror:
                await mirror.cleanup()
                logger.info("Cleaned up mirror sessions")

            return CacheClearResponse(
                status="success",
                message=f"Cache cleared successfully - {cleared_entries} entries removed"
            )
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @app.get("/cache/stats", response_model=CacheStatsResponse, responses={500: {"model": ErrorResponse}})
    async def cache_stats(bypasser: CloakBypasser = Depends(get_bypasser)):
        """Get detailed cache statistics including active entries and hostnames."""
        try:
            if not bypasser:
                return CacheStatsResponse(
                    cached_entries=0,
                    total_hostnames=0,
                    hostnames=[]
                )

            cache = bypasser.cookie_cache.cache
            active_entries = sum(1 for cached in cache.values() if not cached.is_expired())
            expired_entries = len(cache) - active_entries

            logger.info(f"Cache stats: {active_entries} active, {expired_entries} expired, {len(cache)} total")

            return CacheStatsResponse(
                cached_entries=active_entries,
                total_hostnames=len(cache),
                hostnames=list(cache.keys())
            )
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
    async def mirror_request(
        request: Request,
        path: str = "",
        mirror: RequestMirror = Depends(get_mirror),
    ):
        """Dynamic request mirroring endpoint keyed off the x-hostname header."""

        if path.startswith("cache/"):
            raise HTTPException(status_code=404, detail="Not found")

        try:
            start_time = time.time()

            headers = dict(request.headers)

            hostname = None
            proxy = None
            bypass_cache = False

            for key, value in headers.items():
                key_lower = key.lower()
                if key_lower == 'x-hostname':
                    hostname = value
                elif key_lower == 'x-proxy':
                    proxy = value
                elif key_lower == 'x-bypass-cache':
                    bypass_cache = value.lower() in ('true', '1', 'yes', 'on')

            # x-hostname must be a bare host; tolerate a mistaken full URL by stripping it
            if hostname and "://" in hostname:
                parsed = urlparse(hostname)
                corrected = parsed.netloc or parsed.path
                logger.warning(f"x-hostname should be a bare host, not a URL; using '{corrected}' from '{hostname}'")
                hostname = corrected

            if not hostname:
                raise HTTPException(
                    status_code=400,
                    detail="x-hostname header is required for request mirroring"
                )

            if not is_safe_url(f"https://{hostname}"):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid or unsafe hostname - localhost and private IPs are not allowed"
                )

            if proxy and not proxy.startswith(PROXY_SCHEMES):
                raise HTTPException(
                    status_code=400,
                    detail="x-proxy must start with http://, https://, socks4://, or socks5://"
                )

            request_path = f"/{path}" if path else "/"
            logger.info(f"Mirroring {request.method} request to {hostname}{request_path}")
            if proxy:
                logger.info(f"Using proxy: {proxy}")
            if bypass_cache:
                logger.info("x-bypass-cache header detected - forcing fresh cookie generation")

            body = await request.body()

            query_string = str(request.query_params)

            status_code, response_headers, response_content = await mirror.mirror_request(
                method=request.method,
                path=request_path,
                query_string=query_string,
                headers=headers,
                hostname=hostname,
                proxy=proxy,
                bypass_cache=bypass_cache,
                body=body
            )

            processing_time = int((time.time() - start_time) * 1000)

            logger.info(f"Request to {hostname} completed with status {status_code} in {processing_time}ms")
            logger.info(f"Response size: {len(response_content)} bytes")

            response = Response(
                content=response_content,
                status_code=status_code,
                headers=response_headers
            )

            response.headers["x-cf-bypasser-version"] = APP_VERSION
            response.headers["x-processing-time-ms"] = str(processing_time)
            response.headers["x-cache-bypassed"] = str(bypass_cache).lower()

            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error mirroring request: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
