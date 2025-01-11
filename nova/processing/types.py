from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np


@dataclass
class Document:
    """Represents a document to be processed."""
    content: str
    source: str
    metadata: Dict = field(default_factory=dict)


@dataclass
class Chunk:
    """Represents a chunk of text with optional embedding."""
    content: str
    chunk_id: str
    source: str = ""  # Source document/file
    embedding: Optional[np.ndarray] = None
    metadata: Dict = field(default_factory=dict)
    is_ephemeral: bool = False
    expiration: Optional[float] = None


@dataclass
class SearchResult:
    """Represents a search result with relevance score."""
    chunk: Chunk
    score: float
    metadata: Dict = field(default_factory=dict) 