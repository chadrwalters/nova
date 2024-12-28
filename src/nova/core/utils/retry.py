"""Retry utilities for Nova."""

import asyncio
import functools
import random
from typing import Any, Callable, Optional, Type, Union, List, Dict

from ..config.base import RetryConfig
from ..errors import PipelineError
from ..logging import get_logger

logger = get_logger(__name__)


class RetryHandler:
    """Handler for retry operations."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize retry handler.
        
        Args:
            config: Optional retry configuration
        """
        self.config = config or {}
        self.retry_config = RetryConfig(
            max_retries=self.config.get('max_retries', 3),
            delay_between_retries=self.config.get('delay_between_retries', 1.0),
            backoff_factor=self.config.get('backoff_factor', 2.0),
            jitter=self.config.get('jitter', True),
            retry_on_errors=self.config.get('retry_on_errors', [])
        )

    async def retry_operation(self, operation: Callable, *args: Any, **kwargs: Any) -> Any:
        """Retry an operation with configured retry policy.
        
        Args:
            operation: Operation to retry
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation
            
        Returns:
            Operation result
            
        Raises:
            PipelineError: If operation fails after all retries
        """
        retries = 0
        last_error = None
        
        while retries <= self.retry_config.max_retries:
            try:
                if asyncio.iscoroutinefunction(operation):
                    result = await operation(*args, **kwargs)
                else:
                    result = operation(*args, **kwargs)
                return result
                
            except Exception as e:
                last_error = e
                retries += 1
                
                if retries <= self.retry_config.max_retries:
                    delay = self._calculate_delay(retries)
                    logger.warning(f"Operation failed, retrying in {delay:.2f}s ({retries}/{self.retry_config.max_retries})")
                    await asyncio.sleep(delay)
                    
        raise PipelineError(f"Operation failed after {retries} retries: {last_error}")

    def _calculate_delay(self, retry_count: int) -> float:
        """Calculate delay for next retry.
        
        Args:
            retry_count: Current retry count
            
        Returns:
            Delay in seconds
        """
        delay = self.retry_config.delay_between_retries * (
            self.retry_config.backoff_factor ** (retry_count - 1)
        )
        
        if self.retry_config.jitter:
            delay *= random.uniform(0.5, 1.5)
            
        return delay


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
                
            handler = RetryHandler({'retry': retry_config.dict()})
            return await handler.retry_operation(func, *args, **kwargs)
            
        return wrapper
    return decorator 