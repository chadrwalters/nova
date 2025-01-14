"""Error recovery strategies for resource handlers."""

import time
from functools import wraps
from typing import Any, TypeVar
from collections.abc import Callable
from nova.server.errors import ResourceError, ErrorCode

T = TypeVar("T")


def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry decorator for handling transient errors.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay between retries
        exceptions: Tuple of exceptions to catch and retry

    Returns:
        Decorated function that implements retry logic
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_error = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if attempt == max_retries:
                        break
                    time.sleep(current_delay)
                    current_delay *= backoff

            # If we get here, all retries failed
            raise ResourceError(
                message=f"Operation failed after {max_retries} retries: {str(last_error)}",
                code=ErrorCode.RESOURCE_ERROR,
            )

        return wrapper

    return decorator


def graceful_degradation(
    fallback_func: Callable[..., Any] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for implementing graceful degradation.

    Args:
        fallback_func: Optional fallback function to call on failure

    Returns:
        Decorated function that implements graceful degradation
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if fallback_func is not None:
                    try:
                        return fallback_func(*args, **kwargs)
                    except Exception as fallback_error:
                        raise ResourceError(
                            message=f"Operation failed with fallback: Primary: {str(e)}, Fallback: {str(fallback_error)}",
                            code=ErrorCode.RESOURCE_ERROR,
                        )

                raise ResourceError(
                    message=f"Operation failed: {str(e)}",
                    code=ErrorCode.RESOURCE_ERROR,
                )

        return wrapper

    return decorator


def with_fallback_options(
    options: list[Callable[..., Any]],
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for implementing multiple fallback options.

    Args:
        options: List of fallback functions to try in order

    Returns:
        Decorated function that implements fallback options
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            error_list = []
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_list.append(f"Primary: {str(e)}")

            # Try each fallback option
            for i, fallback in enumerate(options):
                try:
                    return fallback(*args, **kwargs)
                except Exception as e:
                    error_list.append(f"Fallback {i + 1}: {str(e)}")

            # If we get here, all options failed
            error_details = "\n".join(error_list)
            raise ResourceError(
                message=f"All operations failed:\n{error_details}",
                code=ErrorCode.RESOURCE_ERROR,
            )

        return wrapper

    return decorator
