"""Pipeline types for Nova document processor."""

from enum import Enum
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from ...phases.parse.processor import MarkdownProcessor
from ...phases.consolidate.processor import MarkdownConsolidateProcessor
from ...phases.aggregate.processor import MarkdownAggregateProcessor
from ...phases.split.processor import ThreeFileSplitProcessor

class PhaseType(str, Enum):
    """Pipeline phase types."""
    
    MARKDOWN_PARSE = "MARKDOWN_PARSE"
    MARKDOWN_CONSOLIDATE = "MARKDOWN_CONSOLIDATE"
    MARKDOWN_AGGREGATE = "MARKDOWN_AGGREGATE"
    MARKDOWN_SPLIT_THREEFILES = "MARKDOWN_SPLIT_THREEFILES"

class PhaseDefinition(BaseModel):
    """Pipeline phase definition."""
    
    description: str
    output_dir: Path
    processor: str
    components: Dict[str, Any]
    
    model_config = ConfigDict(
        extra="allow",
        arbitrary_types_allowed=True
    )
        
class PipelinePhase(BaseModel):
    """Pipeline phase."""
    
    name: str
    definition: PhaseDefinition
    processor: Union[
        MarkdownProcessor,
        MarkdownConsolidateProcessor,
        MarkdownAggregateProcessor,
        ThreeFileSplitProcessor
    ]
    
    model_config = ConfigDict(
        extra="allow",
        arbitrary_types_allowed=True
    ) 