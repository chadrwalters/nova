from pathlib import Path
from typing import Dict, Any, Optional

from ...core.config import ProcessorConfig, PipelineConfig
from ...core.logging import get_logger

logger = get_logger(__name__)

class BaseProcessor:
    """Base class for all processors."""
    
    def __init__(self, processor_config: ProcessorConfig, pipeline_config: PipelineConfig):
        """Initialize processor.
        
        Args:
            processor_config: Processor-specific configuration
            pipeline_config: Global pipeline configuration
        """
        self.processor_config = processor_config
        self.pipeline_config = pipeline_config
        
    async def setup(self):
        """Set up the processor."""
        pass
        
    async def process(self) -> bool:
        """Process content.
        
        Returns:
            True if processing was successful, False otherwise
        """
        raise NotImplementedError("Processors must implement process()")
        
    async def cleanup(self):
        """Clean up resources."""
        pass 