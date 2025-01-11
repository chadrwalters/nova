"""Nova type definitions."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List
import numpy as np


@dataclass
class Document:
    """Represents a document in the system."""
    content: str
    metadata: Dict[str, Any]
    source_path: Path


@dataclass
class Chunk:
    """Represents a chunk of text with optional embedding."""
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None
    is_ephemeral: bool = False
    expiration: Optional[float] = None


@dataclass
class ContextBlock:
    """Represents a block of context for MCP."""
    content: str
    metadata: Dict[str, Any]
    ephemeral: bool = False


@dataclass
class MCPPayload:
    """Model Context Protocol payload."""
    system_instructions: str
    developer_instructions: str
    user_message: str
    context_blocks: List[ContextBlock]


@dataclass
class ConversionResult:
    """Result of a document conversion."""
    success: bool
    content: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlaceholderResult:
    """Placeholder for failed conversions."""
    original_path: Path
    error_message: str
    metadata: Dict[str, Any]


@dataclass
class SearchResult:
    """Result from vector store search."""
    chunk: Chunk
    score: float
    metadata: Dict[str, Any]


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    metadata: Dict
    usage: Dict
