import json
import logging
import os
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class CachedCookies:
    hostname: str
    cookies: Dict[str, str]
    user_agent: str
    timestamp: datetime
    expires_at: datetime
    
    def is_expired(self) -> bool:
        return datetime.now() >= self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'hostname': self.hostname,
            'cookies': self.cookies,
            'user_agent': self.user_agent,
            'timestamp': self.timestamp.isoformat(),
            'expires_at': self.expires_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CachedCookies':
        return cls(
            hostname=data['hostname'],
            cookies=data['cookies'],
            user_agent=data['user_agent'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            expires_at=datetime.fromisoformat(data['expires_at'])
        )


class CookieCache:
    """Thread-safe cache for Cloudflare clearance cookies."""
    
    def __init__(self, cache_file: str = "cf_cookie_cache.json"):
        self.cache_file = cache_file
        self.cache: Dict[str, CachedCookies] = {}
        self.lock = threading.RLock()
        self._load_cache()
    
    def _load_cache(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    for hostname, cached_data in data.items():
                        try:
                            self.cache[hostname] = CachedCookies.from_dict(cached_data)
                        except Exception as e:
                            logging.warning(f"Failed to load cached data for {hostname}: {e}")
        except Exception as e:
            logging.warning(f"Failed to load cache file: {e}")
    
    def _save_cache(self):
        try:
            with open(self.cache_file, 'w') as f:
                data = {hostname: cached.to_dict() for hostname, cached in self.cache.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save cache file: {e}")
    
    def get(self, hostname: str) -> Optional[CachedCookies]:
        with self.lock:
            cached = self.cache.get(hostname)
            if cached and not cached.is_expired():
                logging.info(f"Using cached cookies for {hostname}")
                return cached
            elif cached and cached.is_expired():
                logging.info(f"Cached cookies for {hostname} expired, removing")
                del self.cache[hostname]
                self._save_cache()
            return None
    
    def set(self, hostname: str, cookies: Dict[str, str], user_agent: str, ttl_hours: int = 2):
        with self.lock:
            expires_at = datetime.now() + timedelta(hours=ttl_hours)
            cached = CachedCookies(
                hostname=hostname,
                cookies=cookies,
                user_agent=user_agent,
                timestamp=datetime.now(),
                expires_at=expires_at
            )
            self.cache[hostname] = cached
            self._save_cache()
            logging.info(f"Cached cookies for {hostname}, expires at {expires_at}")
    
    def clear_expired(self):
        with self.lock:
            expired_keys = [k for k, v in self.cache.items() if v.is_expired()]
            for key in expired_keys:
                del self.cache[key]
            if expired_keys:
                self._save_cache()
                logging.info(f"Cleared {len(expired_keys)} expired cache entries")
    
    def invalidate(self, hostname: str):
        with self.lock:
            if hostname in self.cache:
                del self.cache[hostname]
                self._save_cache()
                logging.info(f"Invalidated cache for {hostname}")
    
    def clear_all(self):
        with self.lock:
            self.cache.clear()
            self._save_cache()
            logging.info("Cleared all cache entries")