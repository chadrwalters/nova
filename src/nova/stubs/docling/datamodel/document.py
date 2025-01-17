"""Type stubs for docling.datamodel.document module."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any


class Document:
    """Document class for representing structured documents."""

    def __init__(self, name: str) -> None:
        """Initialize document.

        Args:
            name: Document name
        """
        self.name = name
        self.text = ""
        self.metadata: dict[str, Any] = {}
        self.pictures: list[Any] = []

    def save(self, path: Path) -> None:
        """Save document to path."""
        pass


class DocumentStore:
    """Store for managing documents."""

    def __init__(self, path: Path) -> None:
        """Initialize store."""
        self.path = path

    def get_document(self, name: str) -> Document:
        """Get document by name."""
        return Document(name)

    def list_documents(self) -> Iterator[Document]:
        """List all documents."""
        yield Document("test")
