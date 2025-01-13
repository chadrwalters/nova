"""Exceptions for the Bear parser module."""


class BearParserError(Exception):
    """Base exception for Bear parser errors."""

    pass


class AttachmentError(BearParserError):
    """Exception raised when there is an error processing a Bear attachment."""

    pass


class ValidationError(BearParserError):
    """Exception raised when note validation fails."""

    pass


class FileNotFoundError(BearParserError):
    """Exception raised when a required file is not found."""

    pass


class ParseError(BearParserError):
    """Exception raised when parsing a Bear note fails."""

    pass
