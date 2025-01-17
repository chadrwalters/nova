"""Base models for docling."""

from enum import Enum, auto


class InputFormat(Enum):
    """Input format enum."""

    MD = auto()
    HTML = auto()
    PDF = auto()
    DOCX = auto()
    XLSX = auto()
    PPTX = auto()
    RST = auto()
    ASCIIDOC = auto()
    ORG = auto()
    WIKI = auto()
    LATEX = auto()
    TEXT = auto()

    def __str__(self) -> str:
        """Return string representation."""
        return self.name.lower()


# Format to MIME type mapping
FORMAT_TO_MIME = {
    InputFormat.MD: "text/markdown",
    InputFormat.HTML: "text/html",
    InputFormat.PDF: "application/pdf",
    InputFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    InputFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    InputFormat.PPTX: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    InputFormat.RST: "text/x-rst",
    InputFormat.ASCIIDOC: "text/asciidoc",
    InputFormat.ORG: "text/org",
    InputFormat.WIKI: "text/wiki",
    InputFormat.LATEX: "text/latex",
    InputFormat.TEXT: "text/plain",
}

# Format to file extension mapping
FORMAT_TO_EXT = {
    InputFormat.MD: ".md",
    InputFormat.HTML: ".html",
    InputFormat.PDF: ".pdf",
    InputFormat.DOCX: ".docx",
    InputFormat.XLSX: ".xlsx",
    InputFormat.PPTX: ".pptx",
    InputFormat.RST: ".rst",
    InputFormat.ASCIIDOC: ".asciidoc",
    InputFormat.ORG: ".org",
    InputFormat.WIKI: ".wiki",
    InputFormat.LATEX: ".tex",
    InputFormat.TEXT: ".txt",
}

# MIME type to format mapping
MIME_TO_FORMAT = {mime: fmt for fmt, mime in FORMAT_TO_MIME.items()}

# File extension to format mapping
EXT_TO_FORMAT = {ext: fmt for fmt, ext in FORMAT_TO_EXT.items()}
