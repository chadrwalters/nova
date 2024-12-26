"""Base processor module."""

from pathlib import Path
from typing import Dict, Any, Union

from ..config import PipelineConfig, ProcessorConfig
from ..logging import get_logger

logger = get_logger(__name__)

class BaseProcessor:
    """Base class for all processors."""
    
    def __init__(self, processor_config: ProcessorConfig, pipeline_config: PipelineConfig):
        """Initialize base processor.
        
        Args:
            processor_config: Processor configuration
            pipeline_config: Pipeline configuration
        """
        self.processor_config = processor_config
        self.pipeline_config = pipeline_config
        
        # Standard directory setup that all processors must use
        self.base_dir = Path(pipeline_config.paths.base_dir)
        self.input_dir = Path(pipeline_config.input_dir)
        self.output_dir = Path(processor_config.output_dir)
        self.processing_dir = Path(pipeline_config.processing_dir)
        self.temp_dir = Path(pipeline_config.temp_dir)
        
        # Validate required directories
        if not self.base_dir or not self.input_dir or not self.output_dir:
            raise ValueError("Missing required directory configuration")
            
    async def setup(self) -> bool:
        """Set up processor.
        
        Returns:
            True if setup was successful, False otherwise
        """
        try:
            # Create required directories
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.processing_dir.mkdir(parents=True, exist_ok=True)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Validate input directory exists
            if not self.input_dir.exists():
                logger.error(f"Input directory not found: {self.input_dir}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Failed to set up processor: {str(e)}")
            return False
    
    async def process(self) -> bool:
        """Process files.
        
        Returns:
            True if processing completed successfully, False otherwise
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Processors must implement process()")
        
    async def cleanup(self) -> None:
        """Clean up processor.
        
        This method should be overridden by processors that need cleanup.
        """
        pass
        
    def get_relative_path(self, path: Path) -> Path:
        """Get path relative to base directory.
        
        Args:
            path: Path to get relative path for
            
        Returns:
            Path relative to base directory
        """
        return path.relative_to(self.base_dir)
        
    def get_output_path(self, relative_path: Path) -> Path:
        """Get output path for a file.
        
        Args:
            relative_path: Path relative to base directory
            
        Returns:
            Full output path
        """
        return self.output_dir / relative_path