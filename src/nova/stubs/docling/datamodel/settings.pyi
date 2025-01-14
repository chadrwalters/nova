"""Type stubs for docling.datamodel.settings module."""

class FormatToExtensions:
    """Format to file extensions mapping."""

    @classmethod
    def detect_format(cls, extension: str) -> str: ...

class FormatToMimeType:
    """Format to MIME type mapping."""

    @classmethod
    def detect_format(cls, mime_type: str) -> str: ...
