"""Document model for docling."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .base_models import InputFormat

@dataclass
class Document:
    """Document model."""

    content: str
    """The document content."""

    format: InputFormat
    """The document format."""

    title: Optional[str] = None
    """The document title."""

    tags: List[str] = field(default_factory=list)
    """The document tags."""

    metadata: Dict[str, str] = field(default_factory=dict)
    """Additional metadata."""

    source_path: Optional[Path] = None
    """The source file path."""
