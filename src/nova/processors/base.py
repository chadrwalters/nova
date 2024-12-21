"""Base processor module for Nova document processor."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional

from ..core.config import ProcessorConfig, NovaConfig
from ..core.errors import ProcessingError
from ..core.logging import get_logger

class BaseProcessor(ABC):
    """Base class for all processors."""
    
    def __init__(self, processor_config: ProcessorConfig, nova_config: NovaConfig):
        """Initialize processor.
        
        Args:
            processor_config: Processor-specific configuration
            nova_config: Global Nova configuration
        """
        self.config = processor_config
        self.nova_config = nova_config
        self.logger = get_logger(self.__class__.__name__)
        self._setup()
    
    @abstractmethod
    def _setup(self) -> None:
        """Setup processor requirements."""
        pass
    
    @abstractmethod
    def process(self, input_path: Path, output_path: Path) -> Path:
        """Process a file.
        
        Args:
            input_path: Path to input file
            output_path: Path to output file
            
        Returns:
            Path to processed file
        """
        pass
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Cache processing result.
        
        Args:
            cache_key: Cache key
            result: Result to cache
        """
        # TODO: Implement caching
        pass