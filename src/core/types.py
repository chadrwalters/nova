from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Union


class ProcessingPhase(Enum):
    """Processing phases."""

    HTML_INDIVIDUAL = auto()
    MARKDOWN_CONSOLIDATED = auto()
    HTML_CONSOLIDATED = auto()
    PDF = auto()
    ALL = auto()


@dataclass
class DocumentMetadata:
    """Document metadata."""

    title: str = ""
    date: datetime = field(default_factory=datetime.now)
    author: Optional[str] = None
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    summary: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    keywords: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    related_docs: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Union[str, int, float, bool, List, Dict]] = field(
        default_factory=dict
    )


@dataclass
class ProcessedDocument:
    """Represents a processed markdown document."""

    content: str
    metadata: DocumentMetadata
    warnings: List[str] = field(default_factory=list)
    attachments: List[Path] = field(default_factory=list)
    is_valid: bool = True
    error: Optional[str] = None


@dataclass
class ConsolidationResult:
    """Result of document consolidation."""

    content: str  # The consolidated HTML content
    html_files: List[Path]  # List of individual HTML files
    consolidated_html: Path  # Path to consolidated HTML file
    warnings: List[str]
    metadata: List[DocumentMetadata]


@dataclass
class ExtractedMetadata:
    """Result of metadata extraction."""

    metadata: DocumentMetadata
    content: str
    is_valid: bool
    error: Optional[str]
    warnings: List[str] = field(default_factory=list)


@dataclass
class ProcessedAttachment:
    """Result of attachment processing."""

    source_path: Path
    target_path: Path
    metadata: Dict[str, Union[str, int, bool]]
    is_valid: bool
    error: Optional[str]
