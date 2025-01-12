"""Nova Bear Parser Module.

This module provides functionality for parsing Bear.app note exports, including:
- Parsing Bear note markdown files
- Handling Bear attachments and images
- Extracting metadata like tags and creation dates
- OCR processing for images using Docling
"""

from .parser import BearParser, BearNote, BearAttachment
from .exceptions import BearParserError, AttachmentError, OCRError

__all__ = [
    "BearParser",
    "BearNote",
    "BearAttachment",
    "BearParserError",
    "AttachmentError",
    "OCRError",
]
