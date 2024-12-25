"""
Retry utilities for handling transient failures.
"""

import asyncio
import functools
import logging
import time
from typing import Type, Tuple, Optional, Callable, Any, List

from nova.core.errors import NovaError
from nova.core.utils.error_tracker import ErrorTracker

logger = logging.getLogger(__name__)

def async_retry(
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (NovaError,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Retry decorator for async functions.
    
    Args:
        retries: Maximum number of retries
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay between retries
        exceptions: Tuple of exceptions to catch and retry
        on_retry: Optional callback function called on each retry
        
    Returns:
        Decorated function that will retry on specified exceptions
    """
    retry_config = RetryConfig(
        max_retries=retries,
        delay_between_retries=delay,
        backoff_factor=backoff,
        retry_on_errors=[e.__name__ for e in exceptions]
    )
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = retry_config.delay_between_retries
            
            for attempt in range(retry_config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == retry_config.max_retries:
                        raise
                    
                    if on_retry:
                        on_retry(e, attempt)
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{retry_config.max_retries} failed: {str(e)}. "
                        f"Retrying in {current_delay:.2f}s..."
                    )
                    
                    await asyncio.sleep(current_delay)
                    current_delay *= retry_config.backoff_factor
            
            raise last_exception
        
        return wrapper
    
    return decorator

def retry(
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (NovaError,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Retry decorator for synchronous functions.
    
    Args:
        retries: Maximum number of retries
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay between retries
        exceptions: Tuple of exceptions to catch and retry
        on_retry: Optional callback function called on each retry
        
    Returns:
        Decorated function that will retry on specified exceptions
    """
    retry_config = RetryConfig(
        max_retries=retries,
        delay_between_retries=delay,
        backoff_factor=backoff,
        exceptions=exceptions
    )
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = retry_config.delay_between_retries
            
            for attempt in range(retry_config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_config.exceptions as e:
                    last_exception = e
                    error_tracker.record_error(e)
                    
                    # Check if error is recoverable and should be retried
                    if not getattr(e, 'retry', False):
                        raise
                    
                    if attempt == retry_config.max_retries:
                        logger.error(
                            "Failed after %d retries: %s",
                            retry_config.max_retries, str(e)
                        )
                        raise
                    
                    if on_retry:
                        on_retry(e, attempt + 1)
                    
                    logger.warning(
                        "Attempt %d/%d failed: %s. Retrying in %.1f seconds...",
                        attempt + 1, retry_config.max_retries, str(e), current_delay
                    )
                    
                    # Apply backoff if specified
                    if getattr(last_exception, 'backoff', False):
                        time.sleep(current_delay)
                        current_delay *= retry_config.backoff_factor
                    else:
                        time.sleep(current_delay)
            
            if last_exception:
                raise last_exception
        return wrapper
    return decorator 