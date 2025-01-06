"""Document metadata model."""

import json
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

from nova.context_processor.core.metadata import DocumentMetadata as CoreDocumentMetadata


class DocumentMetadata(CoreDocumentMetadata):
    """Document metadata.

    .. deprecated:: 1.0
       Use nova.core.metadata.DocumentMetadata instead.
    """

    def __init__(self, title: str = "") -> None:
        """Initialize document metadata.

        Args:
            title: Document title.
        """
        warnings.warn(
            "nova.context_processor.models.document.DocumentMetadata is deprecated. "
            "Use nova.core.metadata.DocumentMetadata instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(Path(title) if title else Path())
        self.references: List[
            str
        ] = []  # Override Dict[str, str] with List[str] to match core

    @classmethod
    def from_file(
        cls,
        file_path: Path,
        handler_name: Optional[str] = None,
        handler_version: Optional[str] = None,
    ) -> "DocumentMetadata":
        """Create metadata from file.

        Args:
            file_path: Path to file.
            handler_name: Optional handler name.
            handler_version: Optional handler version.

        Returns:
            Document metadata.
        """
        metadata = cls(title=file_path.stem)
        metadata.file_path = file_path
        metadata.handler_name = handler_name
        metadata.handler_version = handler_version
        return metadata

    def add_error(self, handler: str, message: str) -> None:
        """Add an error.

        Args:
            handler: Handler name.
            message: Error message.
        """
        self.errors[handler] = message
        self.has_errors = True

    def add_output_file(self, file_path: Path) -> None:
        """Add an output file.

        Args:
            file_path: Output file path.
        """
        self.output_files.add(file_path)

    def get_references(self) -> List[str]:
        """Get references.

        Returns:
            List of references.
        """
        return self.references

    def to_json(self) -> str:
        """Convert metadata to JSON string.

        Returns:
            JSON string.
        """
        data = {
            "title": self.title,
            "processed": self.processed,
            "metadata": self.metadata,
            "errors": self.errors,
            "output_files": [str(p) for p in self.output_files],
            "handler_name": self.handler_name,
            "handler_version": self.handler_version,
            "file_path": str(self.file_path) if self.file_path else None,
            "unchanged": self.unchanged,
            "reprocessed": self.reprocessed,
            "references": self.references,
        }
        return json.dumps(data, indent=2)

    def save(self, output_path: Optional[Path] = None) -> None:
        """Save metadata to file.

        Args:
            output_path: Optional output path. If not provided, uses default.
        """
        super().save(output_path)
