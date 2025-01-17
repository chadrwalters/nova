"""Type stubs for docling_core.types.doc.document module."""

from pathlib import Path
from typing import Any

class Document:
    """Document class for representing structured documents."""

    name: str
    text: str
    metadata: dict[str, Any]
    pictures: list[Any]

    def __init__(self, name: str) -> None: ...
    def save(self, path: Path) -> None: ...
