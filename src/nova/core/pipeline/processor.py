"""Processor implementations for Nova document processor."""

from pathlib import Path
from typing import Dict, Any, Optional, List

from ..config import ProcessorConfig, PipelineConfig
from ..errors import ProcessingError
from ..utils.logging import get_logger
from .base import BaseProcessor

logger = get_logger(__name__)

class BaseProcessor:
    """Base class for all processors."""
    
    def __init__(self, processor_config: ProcessorConfig, nova_config: ProcessorConfig):
        """Initialize the processor.
        
        Args:
            processor_config: Processor-specific configuration
            nova_config: Global Nova configuration
        """
        self.processor_config = processor_config
        self.nova_config = nova_config
        self.logger = get_logger(self.__class__.__name__)
    
    def process(self, input_file: Path) -> Dict[str, Any]:
        """Process the input file.
        
        Args:
            input_file: Path to input file
            
        Returns:
            Dictionary containing processing results
            
        Raises:
            ProcessingError: If processing fails
        """
        raise NotImplementedError("Subclasses must implement process()")
    
    def _setup(self):
        """Set up the processor configuration."""
        raise NotImplementedError("Subclasses must implement _setup()")
    
    def _validate_config(self):
        """Validate processor configuration."""
        if not self.processor_config:
            raise ProcessingError("No processor configuration provided")
        if not self.nova_config:
            raise ProcessingError("No Nova configuration provided") 