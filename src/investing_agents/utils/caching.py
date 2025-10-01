"""Simple in-memory caching for data sources.

Provides basic caching to avoid redundant API calls during development and testing.
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


class SimpleCache:
    """Simple in-memory cache with TTL support."""

    def __init__(self, default_ttl_seconds: int = 3600):
        """Initialize cache.

        Args:
            default_ttl_seconds: Default time-to-live in seconds (1 hour)
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl_seconds
        self.hits = 0
        self.misses = 0

    def _make_key(self, *args: Any, **kwargs: Any) -> str:
        """Create cache key from arguments.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Cache key string
        """
        # Create deterministic key from arguments
        key_data = {
            "args": args,
            "kwargs": sorted(kwargs.items()),
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key not in self._cache:
            self.misses += 1
            return None

        entry = self._cache[key]
        expires_at = entry["expires_at"]

        # Check if expired
        if datetime.now() > expires_at:
            logger.debug("cache.expired", key=key[:16])
            del self._cache[key]
            self.misses += 1
            return None

        self.hits += 1
        logger.debug("cache.hit", key=key[:16])
        return entry["value"]

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time-to-live in seconds (uses default if None)
        """
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl)

        self._cache[key] = {
            "value": value,
            "expires_at": expires_at,
            "created_at": datetime.now(),
        }

        logger.debug(
            "cache.set",
            key=key[:16],
            ttl=ttl,
            expires_at=expires_at.isoformat(),
        )

    def clear(self) -> None:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        logger.info("cache.cleared", entries_cleared=count)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "entries": len(self._cache),
        }


# Global cache instance for EDGAR data
edgar_cache = SimpleCache(default_ttl_seconds=86400)  # 24 hours


def cache_edgar_call(func):
    """Decorator to cache EDGAR API calls.

    Example:
        @cache_edgar_call
        async def fetch_companyfacts(ticker):
            # ... fetch from EDGAR ...
            return data
    """

    async def wrapper(*args, **kwargs):
        # Create cache key
        cache_key = edgar_cache._make_key(*args, **kwargs)

        # Check cache
        cached = edgar_cache.get(cache_key)
        if cached is not None:
            logger.info("edgar.cache_hit", args=args[:1])
            return cached

        # Call function
        logger.info("edgar.cache_miss", args=args[:1])
        result = await func(*args, **kwargs)

        # Store in cache
        edgar_cache.set(cache_key, result)

        return result

    return wrapper
