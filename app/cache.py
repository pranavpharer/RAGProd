import hashlib
import threading
import time
from collections import OrderedDict
from typing import Optional


class CacheResp:
    """Bounded, process-local response cache. Use a shared cache for multi-worker fleets."""
    def __init__(self, ttl_secs: int = 200, max_entries: int = 1000):
        self.ttl = ttl_secs
        self.max_entries = max_entries
        self._cache: OrderedDict[str, dict] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._lock = threading.RLock()

    def _keys(self,query:str) -> str:
        normalized = " ".join(query.casefold().split())
        return hashlib.sha256(normalized.encode()).hexdigest() #encode for hashing 

    def get(self,query:str) ->  Optional[str]: # gets response from cache if available and not expired, else returns None
        key = self._keys(query)
        with self._lock:
            data = self._cache.get(key)
            if data and time.monotonic() - data["ts_data"] < self.ttl:
                self._hits += 1
                self._cache.move_to_end(key)
                return data["response"]
            if data:
                del self._cache[key]
            self._misses += 1
            return None


    def set(self,query:str,response:str) -> None: # stores response in cache with current timestamp
        key = self._keys(query)
        if self.ttl <= 0:
            return
        with self._lock:
            self._cache[key] = {"response": response, "ts_data": time.monotonic()}
            self._cache.move_to_end(key)
            while len(self._cache) > self.max_entries:
                self._cache.popitem(last=False)

        
    @property
    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{hit_rate:.1%}",
                "cached_entries": len(self._cache),
            }

if __name__ == "__main__":
    cache = CacheResp(ttl_secs=300)
    result = cache.get('What is Python?')
    print(f'1. First lookup: {result} (miss - nothing cached yet)')

    # Store
    cache.set('What is Python?', 'Python is a programming language.')
    print(f'2. Stored response in cache')
    time.sleep(10)
    # HitW
    result = cache.get('What is Python?')
    print(f'3. Second lookup: {result} (HIT!)')
    # cache._cache[cache._keys("test")] = {"response": "cached response", "ts_data": time.time()}
    # print(cache.get("test"))  # Should return the cached response

    # time.sleep(11)  # Wait for the cache to expire
    # print(cache.get("test"))  # Should return None since the cache has expired
    print(cache.stats)  # Display cache statistics
