"""Document model for Nova."""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class Document:
    """Document class for storing text content and metadata."""
    
    content: str
    source: str
    metadata: Dict[str, Any] 