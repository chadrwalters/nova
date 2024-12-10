import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Iterator, TypeVar

T = TypeVar("T")


def timed(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to measure function execution time.

    Args:
        func: The function to time

    Returns:
        The wrapped function that measures execution time
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        print(f"{func.__name__} took {end - start:.2f} seconds")
        return result

    return wrapper


def get_execution_time(func: Callable[..., T], *args: Any, **kwargs: Any) -> float:
    """Measure execution time of a function.

    Args:
        func: The function to time
        args: Positional arguments for the function
        kwargs: Keyword arguments for the function

    Returns:
        The execution time in seconds
    """
    start = time.perf_counter()
    func(*args, **kwargs)
    end = time.perf_counter()
    return end - start


@contextmanager
def timed_section(name: str) -> Iterator[None]:
    """Context manager for timing code sections.

    Args:
        name: Name of the section being timed

    Yields:
        None
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        end = time.perf_counter()
        print(f"{name} took {end - start:.2f} seconds")
