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


# One browser-init lock per event loop. Keyed by loop so the multi-loop pytest
# harness gets correct mutual exclusion, while production (single loop) shares one.
_browser_init_locks: dict = {}


def get_browser_init_lock() -> asyncio.Lock:
    """Global lock serializing browser launches for the current event loop."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    lock = _browser_init_locks.get(loop)
    if lock is None:
        lock = asyncio.Lock()
        _browser_init_locks[loop] = lock
    return lock
