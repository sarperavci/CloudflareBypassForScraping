"""
Cloudflare Bypasser - Firefox-only impersonation system
"""

__version__ = "2.0.0"
__author__ = "Sarper AVCI"

from .core.bypasser import CamoufoxBypasser
from .core.mirror import RequestMirror
from .cache.cookie_cache import CookieCache
from .utils.config import BrowserConfig
from .server.app import create_app

__all__ = [
    "CamoufoxBypasser",
    "RequestMirror", 
    "CookieCache",
    "BrowserConfig",
    "create_app"
]