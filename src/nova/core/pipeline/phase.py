"""Pipeline phase definitions and configuration."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, Any, Optional, Type

from ..config import ProcessorConfig, PipelineConfig
from .base import BaseProcessor
from ...phases.parse.processor import MarkdownProcessor
from ...phases.consolidate.processor import ConsolidateProcessor
from ...phases.aggregate.processor import AggregateProcessor
from ...phases.split.processor import ThreeFileSplitProcessor

class PhaseType(Enum):
    """Pipeline phase types."""
    MARKDOWN_PARSE = auto()
    MARKDOWN_CONSOLIDATE = auto()
    MARKDOWN_AGGREGATE = auto()
    MARKDOWN_SPLIT_THREEFILES = auto()

@dataclass
class PhaseDefinition:
    """Pipeline phase definition."""
    type: PhaseType
    name: str
    description: str
    processor_class: Type[BaseProcessor]

# Define all pipeline phases
PIPELINE_PHASES = [
    PhaseDefinition(
        type=PhaseType.MARKDOWN_PARSE,
        name="Markdown Parse",
        description="Parse and process markdown files with embedded content",
        processor_class=MarkdownProcessor
    ),
    PhaseDefinition(
        type=PhaseType.MARKDOWN_CONSOLIDATE,
        name="Markdown Consolidate",
        description="Consolidate markdown files with their attachments",
        processor_class=ConsolidateProcessor
    ),
    PhaseDefinition(
        type=PhaseType.MARKDOWN_AGGREGATE,
        name="Markdown Aggregate",
        description="Aggregate all consolidated markdown files into a single file",
        processor_class=AggregateProcessor
    ),
    PhaseDefinition(
        type=PhaseType.MARKDOWN_SPLIT_THREEFILES,
        name="Markdown Split",
        description="Split aggregated markdown into summary, raw notes, and attachments",
        processor_class=ThreeFileSplitProcessor
    )
]

class PipelinePhase:
    """Pipeline phase implementation."""
    
    def __init__(self, definition: PhaseDefinition, processor_config: ProcessorConfig, pipeline_config: PipelineConfig):
        """Initialize pipeline phase.
        
        Args:
            definition: Phase definition
            processor_config: Phase-specific configuration
            pipeline_config: Global pipeline configuration
        """
        self.definition = definition
        self.processor_config = processor_config
        self.pipeline_config = pipeline_config
        self.processor = definition.processor_class(processor_config, pipeline_config)
        self.state: Dict[str, Any] = {}
    
    @property
    def name(self) -> str:
        """Get phase name."""
        return self.definition.name
    
    @property
    def description(self) -> str:
        """Get phase description."""
        return self.definition.description
    
    def process(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Process content through this phase.
        
        Args:
            input_path: Path to input file or directory
            output_path: Path to output file or directory
            
        Returns:
            Dict containing processing results
        """
        # Process content
        result = self.processor.process(input_path, output_path)
        
        # Update state
        self.state.update({
            'last_run': result,
            'status': 'completed'
        })
        
        return result
    
    def get_state(self) -> Dict[str, Any]:
        """Get phase state.
        
        Returns:
            Dict containing phase state
        """
        return {
            'name': self.name,
            'description': self.description,
            'config': self.processor_config.dict(),
            'state': self.state
        } 