"""Error classes for Nova."""

from typing import Dict, Any, Optional

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
    """Base class for all Nova errors."""
    
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
    """Error raised when there is a configuration problem."""
    pass

class ComponentError(NovaError):
    """Error raised when a component fails."""
    pass

class ProcessingError(NovaError):
    """Error raised when processing fails."""
    pass

class ProcessorError(ProcessingError):
    """Error raised when a processor fails."""
    pass

class ParseError(ProcessingError):
    """Error raised when parsing fails."""
    pass

class MarkdownParseError(ParseError):
    """Error raised when markdown parsing fails."""
    pass

class YAMLParseError(ParseError):
    """Error raised when YAML parsing fails."""
    pass

class JSONParseError(ParseError):
    """Error raised when JSON parsing fails."""
    pass

class AttachmentError(ProcessingError):
    """Error raised when attachment processing fails."""
    pass

class AttachmentNotFoundError(AttachmentError):
    """Error raised when an attachment is not found."""
    pass

class InvalidAttachmentError(AttachmentError):
    """Error raised when an attachment is invalid."""
    pass

class AttachmentProcessingError(AttachmentError):
    """Error raised when attachment processing fails."""
    pass

class ImageProcessingError(ProcessingError):
    """Error raised when image processing fails."""
    pass

class ImageNotFoundError(ImageProcessingError):
    """Error raised when an image file is not found."""
    pass

class InvalidImageFormatError(ImageProcessingError):
    """Error raised when an image format is invalid."""
    pass

class ImageConversionError(ImageProcessingError):
    """Error raised when image conversion fails."""
    pass

class ImageMetadataError(ImageProcessingError):
    """Error raised when image metadata processing fails."""
    pass

class DocumentProcessingError(ProcessingError):
    """Error raised when document processing fails."""
    pass

class OfficeProcessingError(ProcessingError):
    """Error raised when office document processing fails."""
    pass

class PipelineError(NovaError):
    """Error raised when pipeline processing fails."""
    pass

class HandlerError(NovaError):
    """Error raised when a handler fails."""
    pass

class ValidationError(NovaError):
    """Error raised when validation fails."""
    pass

class FileError(NovaError):
    """Error raised when file operations fail."""
    pass

class FileOperationError(FileError):
    """Error raised when specific file operations fail."""
    pass

class FileNotFoundError(FileError):
    """Error raised when a file is not found."""
    pass

class FilePermissionError(FileError):
    """Error raised when file permissions are insufficient."""
    pass

class StateError(NovaError):
    """Error raised when state management fails."""
    pass

class CacheError(NovaError):
    """Error raised when cache operations fail."""
    pass

class APIError(NovaError):
    """Error raised when API calls fail."""
    pass

class OpenAIError(APIError):
    """Error raised when OpenAI API calls fail."""
    pass

class DataURIError(NovaError):
    """Error raised when data URI processing fails."""
    pass

class InvalidDataURIError(DataURIError):
    """Error raised when a data URI is invalid."""
    pass

class DataURIEncodingError(DataURIError):
    """Error raised when data URI encoding fails."""
    pass

class DataURIDecodingError(DataURIError):
    """Error raised when data URI decoding fails."""
    pass 