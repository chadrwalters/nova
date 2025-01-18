"""Base models for docling."""

from enum import Enum, auto


class InputFormat(str, Enum):
    """Input format enum."""

    MD = "md"
    HTML = "html"
    PDF = "pdf"
    TEXT = "txt"
    JSON = "json"
    JPEG = "jpeg"
    HEIC = "heic"
    PNG = "png"
    GIF = "gif"
    WEBP = "webp"
    SVG = "svg"


# Format to MIME type mapping
FORMAT_TO_MIME = {
    InputFormat.MD: "text/markdown",
    InputFormat.HTML: "text/html",
    InputFormat.PDF: "application/pdf",
    InputFormat.TEXT: "text/plain",
    InputFormat.JSON: "application/json",
    InputFormat.JPEG: "image/jpeg",
    InputFormat.HEIC: "image/heic",
    InputFormat.PNG: "image/png",
    InputFormat.GIF: "image/gif",
    InputFormat.WEBP: "image/webp",
    InputFormat.SVG: "image/svg+xml",
}

# Format to file extension mapping
FORMAT_TO_EXT = {
    InputFormat.MD: ".md",
    InputFormat.HTML: ".html",
    InputFormat.PDF: ".pdf",
    InputFormat.TEXT: ".txt",
    InputFormat.JSON: ".json",
    InputFormat.JPEG: ".jpg",
    InputFormat.HEIC: ".heic",
    InputFormat.PNG: ".png",
    InputFormat.GIF: ".gif",
    InputFormat.WEBP: ".webp",
    InputFormat.SVG: ".svg",
}

# MIME type to format mapping
MIME_TO_FORMAT = {mime: fmt for fmt, mime in FORMAT_TO_MIME.items()}

# File extension to format mapping
EXT_TO_FORMAT = {ext: fmt for fmt, ext in FORMAT_TO_EXT.items()}
