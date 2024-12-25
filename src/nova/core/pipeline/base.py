"""Base processor module."""

from pathlib import Path
from typing import Dict, Any, Union

from ..config import PipelineConfig, ProcessorConfig
from ..logging import get_logger

logger = get_logger(__name__)

class BaseProcessor:
    """Base processor class."""
    
    def __init__(self, processor_config: Union[ProcessorConfig, Dict[str, Any]], pipeline_config: PipelineConfig):
        """Initialize base processor.
        
        Args:
            processor_config: Processor configuration
            pipeline_config: Pipeline configuration
        """
        logger.debug(f"Initializing processor with config: {processor_config}")
        
        # Create processor config if needed
        if not isinstance(processor_config, ProcessorConfig):
            try:
                processor_config = ProcessorConfig(
                    name=processor_config.get('name', 'unknown'),
                    description=processor_config.get('description', 'Unknown processor'),
                    output_dir=processor_config['output_dir'],
                    processor=processor_config.get('processor', 'UnknownProcessor'),
                    enabled=processor_config.get('enabled', True),
                    components=processor_config.get('components', {}),
                    handlers=processor_config.get('handlers', [])
                )
                logger.debug(f"Created processor config: {processor_config}")
            except Exception as e:
                logger.error(f"Failed to create processor config: {e}")
                logger.debug(f"Config data: {processor_config}")
                raise
        
        self.processor_config = processor_config
        self.pipeline_config = pipeline_config
        self.output_dir = Path(processor_config.output_dir)
        
        # Set up components
        self.components: Dict[str, Any] = {}
        if processor_config.components is not None:
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