"""Type stubs for docling.document_converter module."""

from pathlib import Path
from typing import Any

from .datamodel.base_models import InputFormat
from .datamodel.document import Document


class DocumentConverter:
    """Document converter class."""

    input_dir: str

    def __init__(
        self,
        allowed_formats: list[InputFormat] | None = None,
        format_options: dict[str, Any] | None = None,
    ) -> None:
        ...

    def convert_file(self, path: Path) -> Document:
        """Convert a single file to a Document."""
        raise NotImplementedError

    def convert_all(self, paths: list[Path]) -> list[Document]:
        """Convert multiple files to Documents."""
        raise NotImplementedError

    def add_format_detector(self, detector: Any) -> None:
        """Add a format detector."""
        raise NotImplementedError
