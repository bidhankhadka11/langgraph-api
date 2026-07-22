

import hashlib
import time
from typing import Optional



class ResponseCache:
    """
    In memory response cache with TTL (time to live)

    In production, replace this with Redis for 
    - Presistance accross restarts
    - Shared cache across multiple instances
    - Build in TTL Management
    """

    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self._cache: dict[str, dict] = {}
        self.hits = 0
        self.misses = 0


    def _make_key(self, query: str) -> str:
        """Create a cache key from normalied key"""
        normalized = query.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()


    def get(self, query:str) -> Optional[str]:
        """Get cached response if valid, otherwise return None"""
        key = self._make_key(query)
        
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["timestamp"] < self.ttl:
                self.hits += 1
                return entry["response"]
            else:
                del self._cache[key]

        self.misses += 1
        return None


    def set(self, query: str, response: str) -> None:
        """Cache a response. """
        key = self._make_key(query)
        self._cache[key] = {
            "response": response,
            "timestamp": time.time(),
            "query": query,
        }

    
    @property
    def stats(self) -> dict:
        """Return current cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total) if total > 0 else 0.0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1%}",
            "cached_entries":len(self._cache),
        }
    
        

