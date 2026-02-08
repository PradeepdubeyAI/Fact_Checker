"""Rate limiter and circuit breaker for API calls.

Prevents overwhelming external APIs with too many concurrent requests
and implements circuit breaker pattern for handling service failures.
"""

import asyncio
import logging
import time
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitBreaker:
    """Circuit breaker to prevent retry storms on API failures."""

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 30,
        window_seconds: int = 60,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of 5xx errors before opening circuit
            timeout_seconds: How long to wait before retrying after circuit opens
            window_seconds: Time window to track failures
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.window_seconds = window_seconds
        self.failures = []
        self.is_open = False
        self.opened_at = None
        self._lock = asyncio.Lock()

    async def record_failure(self):
        """Record a failure (5xx error)."""
        async with self._lock:
            current_time = time.time()
            self.failures.append(current_time)

            # Remove old failures outside the window
            self.failures = [
                f for f in self.failures if current_time - f < self.window_seconds
            ]

            # Check if we should open the circuit
            if len(self.failures) >= self.failure_threshold and not self.is_open:
                self.is_open = True
                self.opened_at = current_time
                logger.warning(
                    f"Circuit breaker OPENED after {len(self.failures)} failures. "
                    f"Pausing requests for {self.timeout_seconds}s"
                )

    async def record_success(self):
        """Record a successful call."""
        async with self._lock:
            # Reset on success
            if self.failures:
                self.failures = []
            if self.is_open:
                self.is_open = False
                self.opened_at = None
                logger.info("Circuit breaker CLOSED - service recovered")

    async def check_and_wait(self):
        """Check if circuit is open and wait if needed."""
        async with self._lock:
            if self.is_open:
                current_time = time.time()
                elapsed = current_time - self.opened_at
                
                if elapsed >= self.timeout_seconds:
                    # Try half-open state
                    self.is_open = False
                    self.opened_at = None
                    logger.info("Circuit breaker attempting HALF-OPEN state")
                    return
                else:
                    wait_time = self.timeout_seconds - elapsed
                    logger.warning(
                        f"Circuit breaker is OPEN. Waiting {wait_time:.1f}s before retry"
                    )
                    # Release lock before sleeping
                    pass
        
        # Sleep outside the lock
        if self.is_open:
            await asyncio.sleep(wait_time)


class RateLimiter:
    """Rate limiter with semaphore and circuit breaker."""

    def __init__(self, max_concurrent: int = 4):
        """Initialize rate limiter.

        Args:
            max_concurrent: Maximum number of concurrent API calls
        """
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.circuit_breaker = CircuitBreaker()
        logger.info(f"Rate limiter initialized with max_concurrent={max_concurrent}")

    async def execute(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute function with rate limiting and circuit breaker.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from func
        """
        # Check circuit breaker
        await self.circuit_breaker.check_and_wait()

        # Acquire semaphore
        async with self.semaphore:
            try:
                result = await func(*args, **kwargs)
                await self.circuit_breaker.record_success()
                return result
            except Exception as e:
                # Check if it's a 5xx error
                error_msg = str(e).lower()
                if "500" in error_msg or "502" in error_msg or "503" in error_msg:
                    await self.circuit_breaker.record_failure()
                raise


# Global rate limiter instance
_global_rate_limiter = None


def get_rate_limiter(max_concurrent: int = 4) -> RateLimiter:
    """Get or create global rate limiter instance.

    Args:
        max_concurrent: Maximum concurrent requests (only used on first call)

    Returns:
        RateLimiter instance
    """
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter(max_concurrent=max_concurrent)
    return _global_rate_limiter
