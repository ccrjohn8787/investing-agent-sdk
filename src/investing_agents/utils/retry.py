"""Retry utilities with exponential backoff for handling transient failures."""

import asyncio
import time
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type

import structlog

logger = structlog.get_logger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
):
    """Decorator for retrying async functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        max_delay: Maximum delay in seconds between retries
        exponential_base: Base for exponential backoff calculation
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback function called on each retry

    Example:
        @retry_with_backoff(max_retries=3, initial_delay=1.0)
        async def fetch_data():
            response = await api_call()
            return response

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            last_exception = None

            while attempt <= max_retries:
                try:
                    return await func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e
                    attempt += 1

                    if attempt > max_retries:
                        logger.error(
                            "retry.max_attempts_reached",
                            function=func.__name__,
                            attempts=attempt,
                            error=str(e),
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(initial_delay * (exponential_base ** (attempt - 1)), max_delay)

                    logger.warning(
                        "retry.attempt",
                        function=func.__name__,
                        attempt=attempt,
                        max_retries=max_retries,
                        delay=delay,
                        error=str(e),
                    )

                    # Call custom retry callback if provided
                    if on_retry:
                        on_retry(e, attempt)

                    # Wait before retrying
                    await asyncio.sleep(delay)

            # This should never be reached, but for type safety
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def retry_sync_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
):
    """Decorator for retrying synchronous functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        max_delay: Maximum delay in seconds between retries
        exponential_base: Base for exponential backoff calculation
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback function called on each retry

    Example:
        @retry_sync_with_backoff(max_retries=3, initial_delay=1.0)
        def fetch_data():
            response = api_call()
            return response

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            last_exception = None

            while attempt <= max_retries:
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e
                    attempt += 1

                    if attempt > max_retries:
                        logger.error(
                            "retry.max_attempts_reached",
                            function=func.__name__,
                            attempts=attempt,
                            error=str(e),
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(initial_delay * (exponential_base ** (attempt - 1)), max_delay)

                    logger.warning(
                        "retry.attempt",
                        function=func.__name__,
                        attempt=attempt,
                        max_retries=max_retries,
                        delay=delay,
                        error=str(e),
                    )

                    # Call custom retry callback if provided
                    if on_retry:
                        on_retry(e, attempt)

                    # Wait before retrying
                    time.sleep(delay)

            # This should never be reached, but for type safety
            if last_exception:
                raise last_exception

        return wrapper

    return decorator
