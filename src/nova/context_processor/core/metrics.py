"""Performance metrics tracking for Nova."""
import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar

T = TypeVar("T")


@dataclass
class OperationMetrics:
    """Metrics for a specific operation."""

    name: str
    total_time: float = 0.0
    call_count: int = 0
    min_time: Optional[float] = None
    max_time: Optional[float] = None
    times: List[float] = field(default_factory=list)

    def add_timing(self, duration: float) -> None:
        """Add a timing measurement.

        Args:
            duration: Operation duration in seconds.
        """
        self.total_time += duration
        self.call_count += 1
        self.times.append(duration)

        if self.min_time is None or duration < self.min_time:
            self.min_time = duration
        if self.max_time is None or duration > self.max_time:
            self.max_time = duration

    @property
    def avg_time(self) -> float:
        """Get average operation time."""
        return self.total_time / self.call_count if self.call_count > 0 else 0.0


class MetricsTracker:
    """Performance metrics tracker."""

    def __init__(self) -> None:
        """Initialize metrics tracker."""
        self.operations: Dict[str, OperationMetrics] = {}
        self._lock = asyncio.Lock()

    async def record_operation(
        self,
        operation: str,
        duration: float,
    ) -> None:
        """Record an operation timing.

        Args:
            operation: Operation name.
            duration: Operation duration in seconds.
        """
        async with self._lock:
            if operation not in self.operations:
                self.operations[operation] = OperationMetrics(name=operation)
            self.operations[operation].add_timing(duration)

    def get_metrics_summary(self) -> Dict:
        """Get metrics summary.

        Returns:
            Dictionary with metrics summary.
        """
        return {
            name: {
                "total_time": metrics.total_time,
                "call_count": metrics.call_count,
                "avg_time": metrics.avg_time,
                "min_time": metrics.min_time,
                "max_time": metrics.max_time,
                "times": metrics.times,
            }
            for name, metrics in self.operations.items()
        }


class timing:
    """Context manager and decorator for timing operations."""

    def __init__(
        self,
        operation: str,
        tracker: MetricsTracker,
    ) -> None:
        """Initialize timing context.

        Args:
            operation: Operation name.
            tracker: Metrics tracker instance.
        """
        self.operation = operation
        self.tracker = tracker
        self.start_time: Optional[float] = None

    async def __aenter__(self) -> None:
        """Enter async context."""
        self.start_time = time.time()

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[object],
    ) -> None:
        """Exit async context."""
        if self.start_time is not None:
            duration = time.time() - self.start_time
            await self.tracker.record_operation(self.operation, duration)

    def __call__(
        self, func: Callable[..., Awaitable[T]]
    ) -> Callable[..., Awaitable[T]]:
        """Use as decorator.

        Args:
            func: Async function to wrap

        Returns:
            Wrapped async function
        """

        async def wrapper(*args: Any, **kwargs: Any) -> T:
            """Wrapped function that measures execution time.

            Args:
                *args: Positional arguments
                **kwargs: Keyword arguments

            Returns:
                Result from wrapped function
            """
            async with self:
                return await func(*args, **kwargs)

        return wrapper
