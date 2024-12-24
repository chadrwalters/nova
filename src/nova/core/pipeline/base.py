"""Base processor class for Nova document processor."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..config import ProcessorConfig, PipelineConfig
from ..errors import ProcessingError
from ..utils.logging import get_logger

class BaseProcessor(ABC):
    """Base class for all processors."""
    
    def __init__(self, processor_config: ProcessorConfig, pipeline_config: PipelineConfig):
        """Initialize processor.
        
        Args:
            processor_config: Processor-specific configuration
            pipeline_config: Global pipeline configuration
        """
        self.config = processor_config
        self.pipeline_config = pipeline_config
        self.stats = {
            'errors': 0,
            'warnings': 0,
            'files_processed': 0
        }
        self.logger = get_logger(self.__class__.__name__)
        self._setup()
    
    @abstractmethod
    def _setup(self) -> None:
        """Setup processor requirements."""
        pass
    
    @abstractmethod
    def process(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Process a file or directory.
        
        Args:
            input_path: Path to input file or directory
            output_path: Path to output file or directory
            
        Returns:
            Dictionary containing processing results
            
        Raises:
            ProcessingError: If processing fails
        """
        pass
    
    def _ensure_output_dir(self, output_path: str) -> None:
        """Ensure output directory exists.
        
        Args:
            output_path: Path to output file or directory
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    def _get_output_path(self, input_path: str, output_path: str) -> Path:
        """Get output path for input file.
        
        Args:
            input_path: Path to input file
            output_path: Path to output directory
            
        Returns:
            Path to output file
        """
        input_file = Path(input_path)
        output_dir = Path(output_path)
        
        # If output_path is a directory, maintain input file name
        if output_dir.suffix == '':
            return output_dir / input_file.name
        
        return output_dir
    
    def _handle_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Handle processing error.
        
        Args:
            error: Exception that occurred
            context: Error context
            
        Raises:
            ProcessingError: Always raised with error details
        """
        self.stats['errors'] += 1
        error_msg = f"Processing failed: {str(error)}"
        self.logger.error(error_msg, extra=context)
        raise ProcessingError(error_msg) from error