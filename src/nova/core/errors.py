"""Error handling module for Nova document processor."""

class NovaError(Exception):
    """Base exception for Nova document processor."""
    pass

class ProcessingError(NovaError):
    """Exception raised for errors during document processing."""
    pass

class FileConversionError(ProcessingError):
    """Exception raised for errors during file conversion."""
    pass

class UnsupportedFormatError(ProcessingError):
    """Exception raised for unsupported file formats."""
    pass

class ConfigurationError(NovaError):
    """Exception raised for configuration errors."""
    pass

class StateError(NovaError):
    """Exception raised for state management errors."""
    pass

class ResourceError(NovaError):
    """Exception raised for resource management errors."""
    pass

class ValidationError(NovaError):
    """Exception raised for validation errors."""
    pass

class MarkdownProcessingError(ProcessingError):
    """Error during markdown processing."""
    pass

class ImageProcessingError(ProcessingError):
    """Error during image processing."""
    pass

class DocumentProcessingError(ProcessingError):
    """Error during document processing."""
    pass

def handle_processing_error(error: Exception) -> NovaError:
    """Convert any exception to a Nova error.
    
    Args:
        error: Original exception
        
    Returns:
        Nova error
    """
    if isinstance(error, NovaError):
        return error
    return ProcessingError(str(error))

def cleanup_on_error(func):
    """Decorator to handle cleanup on error.
    
    Args:
        func: The function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            handle_processing_error(e, {
                'function': func.__name__,
                'args': args,
                'kwargs': kwargs
            })
            raise
    return wrapper 