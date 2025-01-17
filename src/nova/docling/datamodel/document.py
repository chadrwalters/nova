"""Document model for docling."""

from dataclasses import dataclass, field
from pathlib import Path

from .base_models import InputFormat


@dataclass
class Document:
    """Document model."""

    content: str
    """The document content."""

    format: InputFormat
    """The document format."""

    title: str | None = None
    """The document title."""

    tags: list[str] = field(default_factory=list)
    """The document tags."""

    metadata: dict[str, str] = field(default_factory=dict)
    """Additional metadata."""

    source_path: Path | None = None
    """The source file path."""
