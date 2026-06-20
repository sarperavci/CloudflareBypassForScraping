import json
import logging
import os
import tempfile
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, Any, Optional

from cf_bypasser.utils.constants import COOKIE_TTL_MINUTES, DEFAULT_CACHE_FILE


@dataclass
class CachedCookies:
    key: str
    cookies: Dict[str, str]
    user_agent: str
    timestamp: datetime
    expires_at: datetime
    exit_ip: Optional[str] = None  # proxy/exit IP at cache time, for the optional IP-change check

    def is_expired(self) -> bool:
        return datetime.now() >= self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            'key': self.key,
            'cookies': self.cookies,
            'user_agent': self.user_agent,
            'timestamp': self.timestamp.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'exit_ip': self.exit_ip,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CachedCookies':
        return cls(
            key=data['key'],
            cookies=data['cookies'],
            user_agent=data['user_agent'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            expires_at=datetime.fromisoformat(data['expires_at']),
            exit_ip=data.get('exit_ip'),
        )


class CookieCache:
    """Thread-safe cache for Cloudflare clearance cookies."""

    def __init__(self, cache_file: str = DEFAULT_CACHE_FILE):
        self.cache_file = cache_file
        self.cache: Dict[str, CachedCookies] = {}
        self.lock = threading.RLock()
        self._load_cache()

    def _load_cache(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    for key, cached_data in data.items():
                        try:
                            self.cache[key] = CachedCookies.from_dict(cached_data)
                        except Exception as e:
                            logging.warning(f"Failed to load cached data for {key}: {e}")
        except (OSError, json.JSONDecodeError, ValueError) as e:
            logging.warning(f"Failed to load cache file: {e}")

    def _save_cache(self):
        data = {key: cached.to_dict() for key, cached in self.cache.items()}
        directory = os.path.dirname(os.path.abspath(self.cache_file))
        fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".cf_cache.", suffix=".tmp")
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.cache_file)  # atomic on POSIX
        except Exception as e:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            logging.error(f"Failed to save cache file: {e}")

    def get(self, key: str) -> Optional[CachedCookies]:
        with self.lock:
            cached = self.cache.get(key)
            if cached and not cached.is_expired():
                logging.info(f"Using cached cookies for {key}")
                return cached
            elif cached and cached.is_expired():
                logging.info(f"Cached cookies for {key} expired, removing")
                del self.cache[key]
                self._save_cache()
            return None

    def set(self, key: str, cookies: Dict[str, str], user_agent: str,
            ttl_minutes: int = COOKIE_TTL_MINUTES, exit_ip: Optional[str] = None):
        with self.lock:
            expires_at = datetime.now() + timedelta(minutes=ttl_minutes)
            cached = CachedCookies(
                key=key,
                cookies=cookies,
                user_agent=user_agent,
                timestamp=datetime.now(),
                expires_at=expires_at,
                exit_ip=exit_ip,
            )
            self.cache[key] = cached
            self._save_cache()
            logging.info(f"Cached cookies for {key}, expires at {expires_at}")

    def clear_expired(self):
        with self.lock:
            expired_keys = [k for k, v in self.cache.items() if v.is_expired()]
            for key in expired_keys:
                del self.cache[key]
            if expired_keys:
                self._save_cache()
                logging.info(f"Cleared {len(expired_keys)} expired cache entries")

    def invalidate(self, key: str):
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                self._save_cache()
                logging.info(f"Invalidated cache for {key}")

    def clear_all(self):
        with self.lock:
            self.cache.clear()
            self._save_cache()
            logging.info("Cleared all cache entries")
