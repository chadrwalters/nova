"""Custom exception classes for the application."""


class NovaError(Exception):
    """Base exception class for Nova errors."""


class ConfigError(NovaError):
    """Configuration related errors."""


class ProcessingError(NovaError):
    """Document processing related errors."""


class ConversionError(NovaError):
    """Document conversion related errors."""


class ConsolidationError(NovaError):
    """Document consolidation related errors."""


class MediaError(NovaError):
    """Media processing related errors."""
