"""Type stubs for docling package."""

from .datamodel.base_models import InputFormat
from .datamodel.document import Document
from .document_converter import DocumentConverter

__all__ = ["DocumentConverter", "InputFormat", "Document"]
