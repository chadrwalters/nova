"""Document model for docling."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
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

    metadata: dict[str, str | date | datetime | list[str]] = field(default_factory=dict)
    """Additional metadata."""

    source_path: Path | None = None
    """The source file path."""

    def __init__(
        self,
        content: str,
        format: InputFormat,
        title: str | None = None,
        tags: Sequence[str] | None = None,
        metadata: dict[str, str | date | datetime | list[str]] | None = None,
        source_path: Path | None = None,
    ):
        self.content = content
        self.format = format
        self.title = title
        self.tags = list(tags) if tags else []
        self.metadata = metadata or {}
        self.source_path = source_path
