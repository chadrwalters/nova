class NovaError(Exception):
    """Base exception for Nova errors."""

    pass


class TemplateError(NovaError):
    """Raised for template-related errors."""

    pass


class ProcessingError(NovaError):
    """Raised for document processing errors."""

    pass


class ConversionError(NovaError):
    """Raised for markdown to HTML conversion errors."""

    pass


class ConsolidationError(NovaError):
    """Raised for HTML consolidation errors."""

    pass


class ConfigurationError(NovaError):
    """Raised for configuration-related errors."""

    pass


class MediaError(NovaError):
    """Raised for media file handling errors."""

    pass
