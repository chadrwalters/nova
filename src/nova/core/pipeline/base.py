"""Base processor for Nova document processor."""

from pathlib import Path
from typing import Dict, Any, Optional, List
import os

from ..config import ProcessorConfig, PipelineConfig, ComponentConfig
from ..logging import get_logger

logger = get_logger(__name__)

class BaseProcessor:
    """Base processor class."""
    
    def __init__(self, processor_config: ProcessorConfig, pipeline_config: PipelineConfig):
        """Initialize base processor.
        
        Args:
            processor_config: Processor configuration
            pipeline_config: Pipeline configuration
        """
        self.processor_config = processor_config
        self.pipeline_config = pipeline_config
        self.output_dir = Path(processor_config.output_dir)
        
        # Set up components
        self.components: Dict[str, Any] = {}
        if hasattr(processor_config, 'components'):
            if not isinstance(processor_config.components, dict):
                processor_config.components = {}
            self.components = processor_config.components
        
    async def setup(self) -> None:
        """Set up processor."""
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def process(self) -> bool:
        """Process files.
        
        Returns:
            True if processing completed successfully, False otherwise
        """
        raise NotImplementedError("Subclasses must implement process()")
        
    async def cleanup(self) -> None:
        """Clean up processor."""
        pass