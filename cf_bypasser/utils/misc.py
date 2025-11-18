from hashlib import md5
from typing import Union
import asyncio

def md5_hash(text: Union[str, bytes]) -> str:
    if isinstance(text, str):
        text = text.encode('utf-8')
    return md5(text).hexdigest()

# Global lock state for browser initialization
_global_lock_state = {"lock": None, "loop": None}

def get_browser_init_lock() -> asyncio.Lock:
    """Get the global browser initialization lock for the current event loop."""
    global _global_lock_state
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.Lock()
        
    if _global_lock_state["lock"] is None or _global_lock_state["loop"] != current_loop:
        _global_lock_state["lock"] = asyncio.Lock()
        _global_lock_state["loop"] = current_loop
        
    return _global_lock_state["lock"] 