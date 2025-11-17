import asyncio
import logging
import traceback
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse, urljoin

from curl_cffi.requests import AsyncSession

from cf_bypasser.core.bypasser import CamoufoxBypasser
from cf_bypasser.utils.config import BrowserConfig


class RequestMirror:
    """Handles dynamic request mirroring with Cloudflare bypass."""
    
    def __init__(self, bypasser: CamoufoxBypasser = None):
        self.bypasser: CamoufoxBypasser = bypasser or CamoufoxBypasser()
        self.session_cache: Dict[str, AsyncSession] = {}  # Cache curl-cffi sessions per hostname
        
    def extract_mirror_headers(self, headers: Dict[str, str]) -> Tuple[Optional[str], Optional[str], bool]:
        """Extract x-hostname, x-proxy, and x-bypass-cache from headers."""
        hostname: Optional[str] = None
        proxy: Optional[str] = None
        bypass_cache: bool = False
        
        # Look for headers (case-insensitive)
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower == 'x-hostname':
                hostname = value
            elif key_lower == 'x-proxy':
                proxy = value
            elif key_lower == 'x-bypass-cache':
                bypass_cache = value.lower() in ('true', '1', 'yes', 'on')
        
        return hostname, proxy, bypass_cache
    
    def strip_mirror_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Remove x-hostname, x-proxy, and x-bypass-cache headers from request."""
        cleaned_headers = {}
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower not in ['x-hostname', 'x-proxy', 'x-bypass-cache']:
                cleaned_headers[key] = value
        return cleaned_headers
    
    def merge_cookies(self, incoming_cookies: str, cf_cookies: Dict[str, str]) -> str:
        """Merge incoming cookies with Cloudflare clearance cookies."""
        try:
            # Parse incoming cookies
            incoming_dict = {}
            if incoming_cookies:
                for cookie in incoming_cookies.split(';'):
                    cookie = cookie.strip()
                    if '=' in cookie:
                        name, value = cookie.split('=', 1)
                        incoming_dict[name.strip()] = value.strip()
            
            # Merge with CF cookies (CF cookies take priority)
            merged_cookies = {**incoming_dict, **cf_cookies}
            
            # Convert back to cookie string
            cookie_pairs = [f"{name}={value}" for name, value in merged_cookies.items()]
            return '; '.join(cookie_pairs)
        except Exception as e:
            logging.error(f"Error merging cookies: {e}")
            # Fallback to CF cookies only
            return '; '.join([f"{name}={value}" for name, value in cf_cookies.items()])
    
    def build_target_url(self, hostname: str, path: str, query_string: str = None) -> str:
        """Build the target URL."""
        if not hostname.startswith(('http://', 'https://')):
            hostname = f"https://{hostname}"
        
        url = urljoin(hostname, path)
        if query_string:
            url += f"?{query_string}"
        
        return url
    
    async def get_session(self, hostname: str, proxy: Optional[str] = None) -> AsyncSession:
        """Get or create a curl-cffi session for the hostname."""
        session_key = f"{hostname}:{proxy or 'no-proxy'}"
        
        if session_key not in self.session_cache:
            proxy_dict = None
            if proxy:
                proxy_dict = {"http": proxy, "https": proxy}
            
            session = AsyncSession(
                impersonate="firefox",  # Use Firefox impersonation
                proxies=proxy_dict,
                timeout=30
            )
            self.session_cache[session_key] = session
        
        return self.session_cache[session_key]
    
    async def mirror_request(
        self,
        method: str,
        path: str,
        query_string: str,
        headers: Dict[str, str],
        body: bytes = None,
        max_retries: int = 2
    ) -> Tuple[int, Dict[str, str], bytes]:
        """Mirror the request to the target hostname with CF bypass."""
        
        # Extract hostname, proxy, and bypass cache flag
        hostname, proxy, bypass_cache = self.extract_mirror_headers(headers)
        
        if not hostname:
            raise ValueError("x-hostname header is required")
        
        for attempt in range(max_retries + 1):
            try:
                logging.info(f"Mirroring {method} request to {hostname}{path} (attempt {attempt + 1}/{max_retries + 1})")
                if bypass_cache:
                    logging.info("x-bypass-cache header detected - forcing fresh cookie generation")
                
                # Get or generate Cloudflare cookies
                target_url = self.build_target_url(hostname, "/")  # Use root for cookie generation
                
                # If bypass_cache is True, invalidate existing cache first
                if bypass_cache:
                    parsed_hostname = urlparse(target_url).netloc
                    self.bypasser.cookie_cache.invalidate(parsed_hostname)
                
                cf_data = await self.bypasser.get_or_generate_cookies(target_url, proxy)
                
                if not cf_data:
                    raise Exception("Failed to get Cloudflare clearance cookies")
                
                # Strip mirror headers and prepare request headers
                clean_headers = self.strip_mirror_headers(headers)
                
                # Override User-Agent with the one used for CF bypass
                clean_headers['user-agent'] = cf_data['user_agent']
                clean_headers.pop("host", None)
                
                # Merge cookies
                incoming_cookies = clean_headers.get('Cookie', '')
                merged_cookies = self.merge_cookies(incoming_cookies, cf_data['cookies'])
                clean_headers['Cookie'] = merged_cookies
                
                # Add Firefox-like headers for better impersonation
                firefox_headers = BrowserConfig.get_firefox_headers()
                for key, value in firefox_headers.items():
                    if key.lower() not in [h.lower() for h in clean_headers.keys()]:
                        clean_headers[key] = value
                
                # Build final target URL
                target_url = self.build_target_url(hostname, path, query_string)
                
                # Get session
                session = await self.get_session(hostname, proxy)
                
                # Make the request
                response = await session.request(
                    method=method,
                    url=target_url,
                    headers=clean_headers,
                    data=body,
                    allow_redirects=False  # Let the client handle redirects
                )
                
                # Convert response headers to dict
                response_headers = dict(response.headers)
                response_content = response.content
                status_code = response.status_code
                
                # Check if we got a 403 Forbidden response
                if status_code == 403 and attempt < max_retries:
                    logging.warning(f"Got 403 Forbidden from {hostname}, invalidating cache and retrying...")
                    
                    # Invalidate the cached cookies for this hostname
                    parsed_hostname = urlparse(target_url).netloc
                    self.bypasser.cookie_cache.invalidate(parsed_hostname)
                    
                    # Wait a bit before retrying
                    await asyncio.sleep(.5)
                    continue
                
                # remove the Content-Encoding and Content-Length headers
                final_headers = {}
                for k, v in response_headers.items():
                    k_lower = k.lower()
                    if k_lower == "content-encoding":
                        final_headers[k] = "identity"
                    elif k_lower == "content-length":
                        final_headers[k] = str(len(response.content))
                
                logging.info(f"Request to {hostname} completed with status {status_code}")
                return status_code, final_headers, response_content
                
            except Exception as e:
                if attempt < max_retries:
                    logging.warning(f"Request attempt {attempt + 1} failed: {e}, retrying...")
                    await asyncio.sleep(.5)
                    continue
                else:
                    logging.error(f"Error mirroring request after {max_retries + 1} attempts: {e}")
                    logging.error(traceback.format_exc())
                    raise
    
    async def cleanup(self):
        """Clean up resources."""
        for session in self.session_cache.values():
            try:
                await session.close()
            except Exception as e:
                logging.error(f"Error closing session: {e}")
        self.session_cache.clear()
        
        if self.bypasser:
            await self.bypasser.cleanup()


class CookieMerger:
    """Utility class for advanced cookie merging logic."""
    
    @staticmethod
    def parse_cookie_string(cookie_string: str) -> Dict[str, str]:
        """Parse cookie string into dictionary."""
        cookies = {}
        if not cookie_string:
            return cookies
        
        for cookie in cookie_string.split(';'):
            cookie = cookie.strip()
            if '=' in cookie:
                name, value = cookie.split('=', 1)
                cookies[name.strip()] = value.strip()
        
        return cookies
    
    @staticmethod
    def cookies_to_string(cookies: Dict[str, str]) -> str:
        """Convert cookie dictionary to string."""
        return '; '.join([f"{name}={value}" for name, value in cookies.items()])
    
    @staticmethod
    def merge_with_priority(
        incoming_cookies: Dict[str, str],
        cf_cookies: Dict[str, str],
        priority_cookies: list = None
    ) -> Dict[str, str]:
        """Merge cookies with priority for specific cookie names."""
        if priority_cookies is None:
            priority_cookies = ['cf_clearance', '__cf_bm', '__cfruid']
        
        merged = dict(incoming_cookies)
        
        # Add CF cookies, giving priority to certain cookies
        for name, value in cf_cookies.items():
            if name in priority_cookies or name not in merged:
                merged[name] = value
        
        return merged
    
    @classmethod
    def advanced_merge(
        cls,
        incoming_cookie_string: str,
        cf_cookies: Dict[str, str]
    ) -> str:
        """Advanced cookie merging with Cloudflare priority."""
        incoming_cookies = cls.parse_cookie_string(incoming_cookie_string)
        merged_cookies = cls.merge_with_priority(incoming_cookies, cf_cookies)
        return cls.cookies_to_string(merged_cookies)