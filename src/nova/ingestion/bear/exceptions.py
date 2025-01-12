"""Exceptions for Bear.app note parsing."""


class BearParserError(Exception):
    """Base exception for Bear parser errors."""

    pass


class InvalidBearExportError(BearParserError):
    """Raised when the Bear export directory structure is invalid."""

    pass


class InvalidBearNoteError(BearParserError):
    """Raised when a Bear note file is malformed."""

    pass


class BearAttachmentError(BearParserError):
    """Raised when there's an error processing a Bear note attachment."""

    pass
