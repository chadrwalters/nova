"""Pipeline types for Nova document processor."""

from enum import Enum
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class PhaseType(str, Enum):
    """Pipeline phase types."""
    
    MARKDOWN_PARSE = "MARKDOWN_PARSE"
    MARKDOWN_CONSOLIDATE = "MARKDOWN_CONSOLIDATE"
    MARKDOWN_AGGREGATE = "MARKDOWN_AGGREGATE"
    MARKDOWN_SPLIT_THREEFILES = "MARKDOWN_SPLIT_THREEFILES"


class ProcessingResult(BaseModel):
    """Result of processing operation."""

    success: bool = True
    processed_files: List[Path] = []
    errors: List[str] = []
    metadata: Dict[str, Any] = {}
    content: Optional[Any] = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra='allow'
    ) 