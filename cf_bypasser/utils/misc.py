from hashlib import md5
from typing import Optional, Union
import asyncio


def md5_hash(text: Union[str, bytes]) -> str:
    if isinstance(text, str):
        text = text.encode('utf-8')
    return md5(text).hexdigest()


def cache_key(hostname: str, proxy: Optional[str] = None) -> str:
    """Cache key for a (hostname, proxy) pair. NUL delimiter avoids concatenation collisions."""
    return md5_hash(f"{hostname}\x00{proxy or ''}")


def per_loop(registry: dict, factory):
    """Return one cached value per running event loop, creating it on first use."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    value = registry.get(loop)
    if value is None:
        value = factory()
        registry[loop] = value
    return value


# One browser-init lock per event loop. Keyed by loop so the multi-loop pytest
# harness gets correct mutual exclusion, while production (single loop) shares one.
_browser_init_locks: dict = {}


def get_browser_init_lock() -> asyncio.Lock:
    """Global lock serializing browser launches for the current event loop."""
    return per_loop(_browser_init_locks, asyncio.Lock)
