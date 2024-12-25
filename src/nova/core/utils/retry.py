"""Retry utilities for Nova."""

import asyncio
import functools
import random
from typing import Any, Callable, Optional, Type, Union, List

from ..config.base import RetryConfig
from ..logging import get_logger

logger = get_logger(__name__)

def async_retry(
    max_retries: Optional[int] = None,
    delay_between_retries: Optional[float] = None,
    backoff_factor: Optional[float] = None,
    jitter: Optional[bool] = None,
    retry_on_errors: Optional[List[Union[Type[Exception], str]]] = None
) -> Callable:
    """Decorator for retrying async functions.
    
    Args:
        max_retries: Maximum number of retries
        delay_between_retries: Initial delay between retries in seconds
        backoff_factor: Factor to multiply delay by after each retry
        jitter: Whether to add random jitter to delay
        retry_on_errors: List of exceptions or error strings to retry on
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get retry config from first argument if it's a class method
            if args and hasattr(args[0], 'config'):
                instance_config = getattr(args[0].config, 'retry', {})
                retry_config = RetryConfig(
                    max_retries=max_retries or instance_config.get('max_retries', 3),
                    delay_between_retries=delay_between_retries or instance_config.get('delay_between_retries', 1.0),
                    backoff_factor=backoff_factor or instance_config.get('backoff_factor', 2.0),
                    jitter=jitter if jitter is not None else instance_config.get('jitter', True),
                    retry_on_errors=retry_on_errors or instance_config.get('retry_on_errors', [])
                )
            else:
                retry_config = RetryConfig(
                    max_retries=max_retries or 3,
                    delay_between_retries=delay_between_retries or 1.0,
                    backoff_factor=backoff_factor or 2.0,
                    jitter=jitter if jitter is not None else True,
                    retry_on_errors=retry_on_errors or []
                )
            
            attempt = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    
                    # Check if we should retry
                    should_retry = False
                    if retry_config.retry_on_errors:
                        for error in retry_config.retry_on_errors:
                            if isinstance(error, str) and error in str(e):
                                should_retry = True
                                break
                            elif isinstance(error, type) and isinstance(e, error):
                                should_retry = True
                                break
                    else:
                        # If no specific errors specified, retry on all exceptions
                        should_retry = True
                    
                    if not should_retry or attempt >= retry_config.max_retries:
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = retry_config.delay_between_retries * (retry_config.backoff_factor ** (attempt - 1))
                    
                    # Add jitter if enabled
                    if retry_config.jitter:
                        delay *= (1 + random.random())
                    
                    logger.warning(
                        f"Attempt {attempt} failed with error: {str(e)}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    
                    await asyncio.sleep(delay)
        
        return wrapper
    
    return decorator 