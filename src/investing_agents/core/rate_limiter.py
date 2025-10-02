"""Rate limiter for API requests.

Implements token bucket algorithm for rate limiting with support for:
- Requests per second (RPS) limits
- Burst capacity
- Async-safe operation
"""

import asyncio
import time
from typing import Optional


class RateLimiter:
    """Token bucket rate limiter for API requests.

    Enforces rate limits by maintaining a bucket of tokens that refill over time.
    Each request consumes one token. If no tokens available, request is delayed.

    Thread-safe and async-safe for use in concurrent applications.
    """

    def __init__(
        self,
        requests_per_second: float,
        burst_capacity: Optional[int] = None,
        name: str = "rate_limiter"
    ):
        """Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests allowed per second
            burst_capacity: Maximum burst size (defaults to RPS if not specified)
            name: Name for logging/identification
        """
        self.requests_per_second = requests_per_second
        self.burst_capacity = burst_capacity or int(requests_per_second)
        self.name = name

        # Token bucket state
        self.tokens = float(self.burst_capacity)
        self.last_refill_time = time.monotonic()

        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens, waiting if necessary.

        Blocks until requested tokens are available, respecting rate limit.

        Args:
            tokens: Number of tokens to acquire (default: 1)
        """
        async with self._lock:
            while True:
                # Refill tokens based on time elapsed
                now = time.monotonic()
                elapsed = now - self.last_refill_time

                # Add tokens based on elapsed time
                self.tokens = min(
                    self.burst_capacity,
                    self.tokens + (elapsed * self.requests_per_second)
                )
                self.last_refill_time = now

                # If enough tokens available, consume and return
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return

                # Not enough tokens - calculate wait time
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.requests_per_second

                # Release lock during wait to allow other tasks
                self._lock.release()
                try:
                    await asyncio.sleep(wait_time)
                finally:
                    await self._lock.acquire()

    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without waiting.

        Non-blocking version of acquire(). Returns immediately.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired, False if not available
        """
        # Refill tokens
        now = time.monotonic()
        elapsed = now - self.last_refill_time
        self.tokens = min(
            self.burst_capacity,
            self.tokens + (elapsed * self.requests_per_second)
        )
        self.last_refill_time = now

        # Try to consume tokens
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def get_wait_time(self, tokens: int = 1) -> float:
        """Get estimated wait time for acquiring tokens.

        Args:
            tokens: Number of tokens needed

        Returns:
            Estimated wait time in seconds (0 if tokens available)
        """
        # Refill tokens
        now = time.monotonic()
        elapsed = now - self.last_refill_time
        current_tokens = min(
            self.burst_capacity,
            self.tokens + (elapsed * self.requests_per_second)
        )

        if current_tokens >= tokens:
            return 0.0

        tokens_needed = tokens - current_tokens
        return tokens_needed / self.requests_per_second

    def reset(self) -> None:
        """Reset rate limiter to full capacity."""
        self.tokens = float(self.burst_capacity)
        self.last_refill_time = time.monotonic()

    def __repr__(self) -> str:
        return (
            f"RateLimiter(name='{self.name}', "
            f"rps={self.requests_per_second}, "
            f"burst={self.burst_capacity}, "
            f"tokens={self.tokens:.2f})"
        )


class BraveSearchRateLimiter(RateLimiter):
    """Rate limiter specifically for Brave Search API.

    Brave Search API rate limits:
    - Free tier: 1 request per second, 2,000 requests per month
    - Pro tier: Higher limits (configured via parameters)
    """

    def __init__(self, tier: str = "free"):
        """Initialize Brave Search rate limiter.

        Args:
            tier: API tier ('free' or 'pro')
        """
        if tier == "free":
            # Free tier: 1 req/sec, no burst
            super().__init__(
                requests_per_second=1.0,
                burst_capacity=1,  # No burst allowed on free tier
                name="brave_search_free"
            )
        elif tier == "pro":
            # Pro tier: Higher limits (adjust as needed)
            super().__init__(
                requests_per_second=10.0,
                burst_capacity=20,
                name="brave_search_pro"
            )
        else:
            raise ValueError(f"Unknown tier: {tier}. Use 'free' or 'pro'")

        self.tier = tier

    def __repr__(self) -> str:
        return f"BraveSearchRateLimiter(tier='{self.tier}', tokens={self.tokens:.2f})"
