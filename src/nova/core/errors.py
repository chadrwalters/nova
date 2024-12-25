"""Error classes for Nova document processor."""

from typing import Any, Dict, Optional, Union, Type, TypeVar, Callable
import asyncio
import functools
import logging

F = TypeVar('F', bound=Callable[..., Any])

class ErrorContext:
    """Context information for errors."""
    
    def __init__(
        self,
        component: str,
        operation: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        self.component = component
        self.operation = operation
        self.details = details or {}
    
    def __str__(self) -> str:
        return f"{self.component}.{self.operation}: {self.details}"

class NovaError(Exception):
    """Base class for Nova errors."""
    
    def __init__(
        self,
        message: str,
        context: Optional[ErrorContext] = None
    ) -> None:
        super().__init__(message)
        self.context = context
        self.details: Dict[str, Any] = {}
    
    def __str__(self) -> str:
        if self.context:
            return f"{super().__str__()} ({self.context})"
        return super().__str__()

class ConfigurationError(NovaError):
    """Error raised for configuration issues."""
    pass

class ComponentError(NovaError):
    """Error raised for component-related issues."""
    pass

class ProcessingError(NovaError):
    """Error raised for processing issues."""
    pass

class ProcessorError(NovaError):
    """Error raised for processor-specific issues."""
    pass

class PipelineError(NovaError):
    """Error raised for pipeline-related issues."""
    pass

class FileError(NovaError):
    """Error raised for file operation issues."""
    pass

class FileOperationError(NovaError):
    """Error raised for file operation failures."""
    pass

class ValidationError(NovaError):
    """Error raised for validation failures."""
    pass

class ParseError(NovaError):
    """Error raised for parsing failures."""
    pass

class HandlerError(NovaError):
    """Error raised for handler failures."""
    pass

class AttachmentError(NovaError):
    """Error raised for attachment handling failures."""
    pass

class AttachmentNotFoundError(AttachmentError):
    """Error raised when an attachment cannot be found."""
    pass

class AttachmentProcessingError(AttachmentError):
    """Error raised when there is a problem processing an attachment."""
    pass

def with_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    exceptions: Union[Type[Exception], tuple[Type[Exception], ...]] = NovaError,
    logger: Optional[logging.Logger] = None
) -> Callable[[F], F]:
    """Decorator to retry functions on failure.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Delay between retries in seconds
        exceptions: Exception types to catch and retry
        logger: Logger instance for retry attempts
    
    Returns:
        Decorated function that implements retry logic
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal logger
            
            if logger is None:
                logger = logging.getLogger(func.__module__)
            
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed: {str(e)}. "
                            f"Retrying in {delay} seconds..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed. "
                            f"Last error: {str(e)}"
                        )
            
            if last_error:
                raise last_error
        
        return wrapper  # type: ignore
    
    return decorator

def handle_errors(logger=None, reraise=True):
    """Decorator for error handling.
    
    Args:
        logger: Optional logger instance
        reraise: Whether to reraise caught errors (defaults to True)
    """
    def decorator(func):
        # Get function name for logging
        func_name = func.__name__
        
        # Handle async functions
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    log = logger or logging.getLogger(__name__)
                    log.error(f"Error in {func_name}: {str(e)}")
                    if reraise:
                        raise
                    return None
            return wrapper
            
        # Handle sync functions
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    log = logger or logging.getLogger(__name__)
                    log.error(f"Error in {func_name}: {str(e)}")
                    if reraise:
                        raise
                    return None
            return wrapper
            
    return decorator

__all__ = [
    'NovaError',
    'ConfigurationError',
    'ComponentError',
    'ProcessingError',
    'ProcessorError',
    'PipelineError',
    'FileError',
    'FileOperationError',
    'ValidationError',
    'ParseError',
    'HandlerError',
    'AttachmentError',
    'AttachmentNotFoundError',
    'AttachmentProcessingError',
    'ErrorContext',
    'with_retry',
    'handle_errors'
] 