"""Pipeline phase implementation."""

from typing import Dict, Any, Optional
from pathlib import Path

from ..config import ProcessorConfig, PipelineConfig
from .types import PhaseDefinition

class PipelinePhase:
    """Pipeline phase implementation."""
    
    def __init__(
        self,
        definition: PhaseDefinition,
        processor_config: ProcessorConfig,
        pipeline_config: PipelineConfig
    ):
        """Initialize pipeline phase.
        
        Args:
            definition: Phase definition
            processor_config: Processor configuration
            pipeline_config: Pipeline configuration
        """
        self.definition = definition
        self.processor_config = processor_config
        self.pipeline_config = pipeline_config
        
        # Set up phase attributes
        self.name = definition.name
        self.description = definition.description
        self.type = definition.type
        
        # Set up phase directories
        phase_dir = Path(pipeline_config.processing_dir) / "phases" / self.type.value.lower()
        input_dir = processor_config.input_dir or Path(pipeline_config.input_dir)
        output_dir = Path(processor_config.output_dir) if processor_config.output_dir else phase_dir
        
        # Update processor configuration
        processor_config.input_dir = str(input_dir)
        processor_config.output_dir = str(output_dir)
        
        # Set up phase state
        self.state = {
            'status': 'not started',
            'input_dir': str(input_dir),
            'output_dir': str(output_dir),
            'phase_dir': str(phase_dir)
        }
        
        # Create processor instance
        processor_class = self.get_processor_class()
        self.processor = processor_class(processor_config, pipeline_config)
    
    def get_processor_class(self):
        """Get processor class based on phase type."""
        from ...phases.parse.processor import MarkdownProcessor
        from ...phases.consolidate.processor import MarkdownConsolidateProcessor
        from ...phases.aggregate.processor import MarkdownAggregateProcessor
        from ...phases.split.processor import ThreeFileSplitProcessor
        
        processor_map = {
            'MARKDOWN_PARSE': MarkdownProcessor,
            'MARKDOWN_CONSOLIDATE': MarkdownConsolidateProcessor,
            'MARKDOWN_AGGREGATE': MarkdownAggregateProcessor,
            'MARKDOWN_SPLIT_THREEFILES': ThreeFileSplitProcessor
        }
        
        processor_class = processor_map.get(self.type.value)
        if not processor_class:
            raise ValueError(f"Unknown processor type: {self.type.value}")
        
        return processor_class
    
    def get_state(self) -> Dict[str, Any]:
        """Get phase state.
        
        Returns:
            Phase state dictionary
        """
        return {
            'name': self.name,
            'description': self.description,
            'type': self.type.name,
            'state': self.state
        }
    
    def process(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Process phase.
        
        Args:
            input_path: Path to input file or directory
            output_path: Path to output file or directory
            
        Returns:
            Dictionary containing processing results
        """
        # Update state
        self.state['status'] = 'processing'
        
        try:
            # Process phase
            result = self.processor.process(input_path, output_path)
            
            # Update state
            self.state['status'] = 'completed'
            self.state.update(result)
            return result
            
        except Exception as e:
            # Update state
            self.state['status'] = 'failed'
            self.state['error'] = str(e)
            raise 