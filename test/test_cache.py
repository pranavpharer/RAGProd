import time
from app.cache import CacheResp



class TestCacheResp:
    
    def setup_method(self):
        self.cache = CacheResp(ttl_secs=2)  # Set a short TTL for testing
        
    def test_cache_miss_return_none(self):
        result = self.cache.get("test_query")
        assert result is None, "Expected None for cache miss"
        
    def test_cache_hit_return_value(self):
        self.cache.set("What is capital of Germany", "Capital is Berlin")
        result = self.cache.get("What is capital of Germany")
        assert result == "Capital is Berlin", "Expected cached value for cache hit"
        
    def test_cache_matching_letter_case(self):
        self.cache.set("What is capital of Germany", "Capital is Berlin")
        result = self.cache.get("what is capital of germany")
        assert result == "Capital is Berlin", "Expected None for case-insensitive cache miss"
        
    def test_cache_expiry(self):
        self.cache.set("What is capital of Germany", "Capital is Berlin")
        time.sleep(3)  # Wait for cache to expire
        result = self.cache.get("What is capital of Germany")
        assert result is None, "Expected None for expired cache entry"
        
    def test_cache_stats(self):
        self.cache.get("miss1")
        self.cache.get("miss2")
        self.cache.set("hit", "value")
        self.cache.get("hit")
        
        stats = self.cache.stats
        assert stats["hits"] == 1, "Expected 1 cache hit"
        assert stats["misses"] == 2, "Expected 2 cache misses"
        assert stats["cached_entries"] == 1, "Expected 1 cached entry" 
        
        
        