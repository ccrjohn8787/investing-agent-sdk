"""Simple in-memory cache for web search results.

Prevents redundant Brave API calls for identical search queries.
"""

import hashlib
import time
from typing import Dict, Optional, Tuple


class SearchCache:
    """In-memory cache for web search results with TTL."""

    def __init__(self, ttl_seconds: int = 3600):
        """Initialize search cache.

        Args:
            ttl_seconds: Time-to-live for cached results (default: 1 hour)
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[str, float]] = {}  # query_hash -> (result, timestamp)

    def _hash_query(self, hypothesis_id: str, questions: list) -> str:
        """Generate cache key from hypothesis and questions.

        Args:
            hypothesis_id: Hypothesis identifier
            questions: List of research questions

        Returns:
            MD5 hash of the query
        """
        query_str = f"{hypothesis_id}::{','.join(questions)}"
        return hashlib.md5(query_str.encode()).hexdigest()

    def get(self, hypothesis_id: str, questions: list) -> Optional[str]:
        """Get cached search results if available and not expired.

        Args:
            hypothesis_id: Hypothesis identifier
            questions: List of research questions

        Returns:
            Cached results or None if not found/expired
        """
        query_hash = self._hash_query(hypothesis_id, questions)

        if query_hash in self._cache:
            result, timestamp = self._cache[query_hash]

            # Check if expired
            if time.time() - timestamp < self.ttl_seconds:
                return result
            else:
                # Remove expired entry
                del self._cache[query_hash]

        return None

    def put(self, hypothesis_id: str, questions: list, result: str) -> None:
        """Cache search results.

        Args:
            hypothesis_id: Hypothesis identifier
            questions: List of research questions
            result: Search results to cache
        """
        query_hash = self._hash_query(hypothesis_id, questions)
        self._cache[query_hash] = (result, time.time())

    def clear(self) -> None:
        """Clear all cached results."""
        self._cache.clear()

    def size(self) -> int:
        """Get number of cached entries."""
        return len(self._cache)

    def evict_expired(self) -> int:
        """Remove expired entries from cache.

        Returns:
            Number of entries evicted
        """
        now = time.time()
        expired = [
            query_hash
            for query_hash, (_, timestamp) in self._cache.items()
            if now - timestamp >= self.ttl_seconds
        ]

        for query_hash in expired:
            del self._cache[query_hash]

        return len(expired)
