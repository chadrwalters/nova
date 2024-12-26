"""Configuration classes for Nova document processor."""

from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ConfigDict

class ProcessorConfig(BaseModel):
    """Base configuration for a processor."""
    output_dir: str
    processor: str
    components: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        self.components = self.components or {}

class PipelineConfig(BaseModel):
    """Configuration for the document processing pipeline."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    phases: Dict[str, ProcessorConfig] = Field(default_factory=dict)
    
    @classmethod
    def load(cls) -> 'PipelineConfig':
        """Load pipeline configuration."""
        # Default configuration for now
        config = cls()
        
        # Add default phases
        config.phases = {
            'markdown_parse': ProcessorConfig(
                output_dir="${NOVA_PHASE_MARKDOWN_PARSE}",
                processor="MarkdownProcessor",
                description="Parse and process markdown files with embedded content",
                components={}
            ),
            'markdown_consolidate': ProcessorConfig(
                output_dir="${NOVA_PHASE_MARKDOWN_CONSOLIDATE}",
                processor="MarkdownConsolidateProcessor",
                description="Consolidate markdown files with their attachments",
                components={}
            ),
            'markdown_aggregate': ProcessorConfig(
                output_dir="${NOVA_PHASE_MARKDOWN_AGGREGATE}",
                processor="MarkdownAggregateProcessor",
                description="Aggregate all consolidated markdown files into a single file",
                components={}
            ),
            'markdown_split': ProcessorConfig(
                output_dir="${NOVA_PHASE_MARKDOWN_SPLIT}",
                processor="ThreeFileSplitProcessor",
                description="Split aggregated markdown into summary, raw notes, and attachments",
                components={}
            )
        }
        
        return config

    def get_phase_id(self, processor_name: str) -> Optional[str]:
        """Get phase ID for a processor.
        
        Args:
            processor_name: Name of the processor
            
        Returns:
            Phase ID if found, None otherwise
        """
        for phase_id, config in self.phases.items():
            if config.processor == processor_name:
                return phase_id
        return None

def load_config() -> PipelineConfig:
    """Load pipeline configuration."""
    return PipelineConfig.load() 