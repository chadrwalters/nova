"""Result model for processor operations."""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from pathlib import Path

@dataclass
class ProcessorResult:
    """Result of a processor operation."""
    
    success: bool = False
    content: str = ""
    processed_files: List[Path] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict) 