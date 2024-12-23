"""Base classes for Nova processors."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
import json

from .config import NovaConfig, ProcessorConfig
from .logging import get_logger

class BaseProcessor(ABC):
    """Base class for all processors."""
    
    def __init__(self, processor_config: ProcessorConfig, nova_config: NovaConfig) -> None:
        """Initialize the processor.
        
        Args:
            processor_config: Configuration specific to this processor
            nova_config: Global Nova configuration
        """
        self.processor_config = processor_config
        self.nova_config = nova_config
        self._setup()
    
    def _setup(self) -> None:
        """Setup processor requirements."""
        # Create output directories
        output_dir = self.nova_config.paths.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create processing directory
        processing_dir = self.nova_config.paths.processing_dir
        processing_dir.mkdir(parents=True, exist_ok=True)

        # Create temp directory
        temp_dir = self.nova_config.paths.temp_dir
        temp_dir.mkdir(parents=True, exist_ok=True)
    
    @abstractmethod
    def process(self, content: str, **kwargs: Any) -> str:
        """Process the content.
        
        Args:
            content: The content to process
            **kwargs: Additional arguments for processing
        
        Returns:
            The processed content
        """
        raise NotImplementedError("Subclasses must implement process()")
    
    def _cache_result(self, cache_path: str, data: Dict[str, Any]) -> None:
        """Cache processing results.
        
        Args:
            cache_path: Path to cache file
            data: Data to cache
        """
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.debug(f"Cached results to {cache_path}")
        except Exception as e:
            self.logger.error(f"Failed to cache results to {cache_path}: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics.
        
        Returns:
            Dictionary containing processor statistics
        """
        return self.stats 