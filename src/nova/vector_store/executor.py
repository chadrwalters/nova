"""Thread pool executor for CPU-bound operations."""

import concurrent.futures
import multiprocessing
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class ThreadPoolExecutor:
    """Thread pool executor for CPU-bound operations."""

    _instance = None
    _executor: concurrent.futures.ThreadPoolExecutor | None = None

    def __new__(cls) -> "ThreadPoolExecutor":
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the executor."""
        if self._executor is None:
            # Use CPU count for optimal performance
            self._executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=multiprocessing.cpu_count(),
                thread_name_prefix="nova_worker",
            )

    @property
    def executor(self) -> concurrent.futures.ThreadPoolExecutor:
        """Get the executor instance.

        Returns:
            Thread pool executor
        """
        if self._executor is None:
            self.__init__()
        assert self._executor is not None  # for type checker
        return self._executor

    def submit(self, fn: Callable[..., T], *args: Any, **kwargs: Any) -> concurrent.futures.Future[T]:
        """Submit a function to the executor.

        Args:
            fn: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Future object
        """
        return self.executor.submit(fn, *args, **kwargs)

    def map(self, fn: Callable[..., T], *iterables: Any) -> list[T]:
        """Map a function over iterables.

        Args:
            fn: Function to execute
            *iterables: Iterables to map over

        Returns:
            List of results
        """
        return list(self.executor.map(fn, *iterables))

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the executor.

        Args:
            wait: Whether to wait for pending futures
        """
        if self._executor:
            self._executor.shutdown(wait=wait)
            self._executor = None


# Global executor instance
executor = ThreadPoolExecutor()
