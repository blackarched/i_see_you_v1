
"""
Device store abstraction.

Provides a dict-like API backed by Redis (if available) or in-memory dict.
Used to store device entries keyed by IP address. Values are JSON-serializable dicts.
"""

import json
import threading
from typing import Dict, Any, Iterator, Optional

try:
    import redis as redislib
except Exception:
    redislib = None

class BaseDeviceStore:
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError
    def set(self, key: str, value: Dict[str, Any]) -> None:
        raise NotImplementedError
    def setdefault(self, key: str, default: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
    def keys(self) -> Iterator[str]:
        raise NotImplementedError
    def items(self) -> Iterator:
        raise NotImplementedError
    def delete(self, key: str) -> None:
        raise NotImplementedError

class InMemoryDeviceStore(BaseDeviceStore):
    def __init__(self):
        self._d = {}
        self._lock = threading.RLock()

    def get(self, key):
        with self._lock:
            return self._d.get(key)

    def set(self, key, value):
        with self._lock:
            self._d[key] = value

    def setdefault(self, key, default):
        with self._lock:
            return self._d.setdefault(key, default)

    def keys(self):
        with self._lock:
            return list(self._d.keys())

    def items(self):
        with self._lock:
            return list(self._d.items())

    def delete(self, key):
        with self._lock:
            if key in self._d:
                del self._d[key]

class RedisDeviceStore(BaseDeviceStore):
    def __init__(self, redis_client, prefix="iseeyou:device:"):
        if redislib is None:
            raise RuntimeError("redis library is required for RedisDeviceStore")
        self._r = redis_client
        self._prefix = prefix

    def _key(self, ip):
        return f"{self._prefix}{ip}"

    def get(self, key):
        raw = self._r.get(self._key(key))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    def set(self, key, value):
        self._r.set(self._key(key), json.dumps(value))

    def setdefault(self, key, default):
        # Use Redis GETSET-like behaviour: fetch, and if missing, set default and return it.
        k = self._key(key)
        raw = self._r.get(k)
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                # On corruption, overwrite with default
                self._r.set(k, json.dumps(default))
                return default
        else:
            self._r.set(k, json.dumps(default))
            return default

    def keys(self):
        pattern = f"{self._prefix}*"
        cursor = "0"
        results = []
        try:
            # Use scan to avoid blocking Redis
            it = self._r.scan_iter(match=pattern)
            for fullkey in it:
                # fullkey may be bytes or str
                fk = fullkey.decode() if isinstance(fullkey, bytes) else fullkey
                ip = fk.replace(self._prefix, "", 1)
                results.append(ip)
        except Exception:
            # fallback: empty
            pass
        return results

    def items(self):
        for ip in self.keys():
            yield (ip, self.get(ip))

    def delete(self, key):
        self._r.delete(self._key(key))
