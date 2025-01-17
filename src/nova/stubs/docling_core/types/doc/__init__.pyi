"""Type stubs for docling_core.types.doc module."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel

class DoclingDocument(BaseModel):
    """Document class for representing structured documents."""

    name: str
    text: str
    metadata: dict[str, Any]
    pictures: list[Any]

    def save(self, path: Path) -> None: ...

__all__ = ["DoclingDocument"]
