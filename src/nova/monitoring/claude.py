"""Claude API monitoring integration."""

import asyncio
import time
from typing import Optional, AsyncGenerator, Any
from anthropic import RateLimitError, APIError

from .metrics import (
    API_REQUESTS,
    API_ERRORS,
    RATE_LIMITS_REMAINING,
    RATE_LIMIT_RESETS
)
from .alerts import AlertManager


class ClaudeMonitor:
    """Monitor for Claude API usage."""

    def __init__(self, alert_manager: AlertManager):
        self.alert_manager = alert_manager
        self._last_rate_limit = float('inf')
        self._rate_limit_reset = 0.0

    def record_request(self, endpoint: str) -> None:
        """Record an API request."""
        API_REQUESTS.labels(service="claude").inc()

    def record_error(self, error_type: str) -> None:
        """Record an API error."""
        API_ERRORS.labels(service="claude", error_type=error_type).inc()

    def update_rate_limits(self, remaining: int, reset_time: int) -> None:
        """Update rate limit metrics."""
        RATE_LIMITS_REMAINING.labels(service="claude").set(remaining)
        RATE_LIMIT_RESETS.labels(service="claude").set(reset_time)
        
        self._last_rate_limit = remaining
        self._rate_limit_reset = reset_time
        
        self.alert_manager.check_rate_limits(remaining, reset_time)

    def check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        return self._last_rate_limit > 0


class MonitoredClaudeClient:
    """Claude client with monitoring support."""

    def __init__(self, monitor: ClaudeMonitor, client: Any):
        self.client = client
        self.monitor = monitor
        self._last_rate_limit = float('inf')
        self._rate_limit_reset = 0.0

    async def complete(
        self,
        mcp_payload: Any,
        retry_count: int = 3,
        retry_delay: float = 1.0
    ) -> str:
        """Monitored completion request."""
        try:
            # Track API request
            API_REQUESTS.labels(service="claude").inc()
            
            # Check rate limits
            if not self.monitor.check_rate_limit():
                raise ValueError("Rate limit exceeded")
                
            start_time = time.time()
            response = await self._complete_with_monitoring(mcp_payload)
            duration = time.time() - start_time
            
            self._update_metrics(duration)
            return response
            
        except Exception as e:
            API_ERRORS.labels(service="claude", error_type="unknown").inc()
            raise

    async def complete_stream(
        self,
        mcp_payload: Any,
        retry_count: int = 3,
        retry_delay: float = 1.0
    ) -> AsyncGenerator[str, None]:
        """Monitored streaming completion request."""
        try:
            # Track API request
            API_REQUESTS.labels(service="claude").inc()
            
            # Check rate limits
            if not self.monitor.check_rate_limit():
                raise ValueError("Rate limit exceeded")
                
            start_time = time.time()
            async for chunk in self._stream_with_monitoring(mcp_payload):
                yield chunk
            duration = time.time() - start_time
            
            self._update_metrics(duration)
            
        except Exception as e:
            API_ERRORS.labels(service="claude", error_type="unknown").inc()
            raise

    async def _complete_with_monitoring(self, mcp_payload: Any) -> str:
        """Single completion attempt with monitoring."""
        start_time = time.time()
        try:
            response = await self.client.complete(mcp_payload)
            self._update_metrics(time.time() - start_time)
            return response
        except Exception as e:
            self._update_metrics(time.time() - start_time, success=False)
            raise

    async def _stream_with_monitoring(self, mcp_payload: Any) -> AsyncGenerator[str, None]:
        """Streaming completion with monitoring."""
        start_time = time.time()
        try:
            stream = await self.client.complete_stream(mcp_payload)
            async for chunk in stream:
                yield chunk
            self._update_metrics(time.time() - start_time)
        except Exception as e:
            self._update_metrics(time.time() - start_time, success=False)
            raise

    def _update_metrics(self, duration: float, success: bool = True) -> None:
        """Update metrics after completion."""
        self.monitor.alert_manager.check_query_latency(duration)
        
        if not success:
            error_count = API_ERRORS.labels(service="claude", error_type="unknown")._value.get()
            request_count = API_REQUESTS.labels(service="claude")._value.get()
            self.monitor.alert_manager.check_error_rate(error_count, request_count)

    def _update_rate_limits(self, error: RateLimitError) -> None:
        """Update rate limit metrics from error."""
        # Extract rate limit info from error
        # This would need to be adapted based on actual error structure
        remaining = getattr(error, 'remaining_requests', 0)
        reset_time = getattr(error, 'reset_time', time.time() + 60)
        
        # Update metrics
        RATE_LIMITS_REMAINING.set(remaining)
        RATE_LIMIT_RESETS.set(reset_time)
        
        # Store for internal use
        self._last_rate_limit = remaining
        self._rate_limit_reset = reset_time
        
        # Check alerts
        self.alert_manager.check_rate_limits(remaining, reset_time)

    async def _handle_rate_limit(self, retry_delay: float) -> None:
        """Handle rate limit with exponential backoff."""
        # Calculate time to wait
        now = time.time()
        if self._rate_limit_reset > now:
            wait_time = self._rate_limit_reset - now
        else:
            wait_time = retry_delay
            
        # Wait before retry
        await asyncio.sleep(wait_time) 