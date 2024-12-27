"""Pipeline phase base class."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
import importlib

from ..config import ProcessorConfig
from ..models.result import ProcessingResult


class Phase:
    """Base class for pipeline phases."""
    
    def __init__(self, name: str, config: ProcessorConfig):
        """Initialize the phase.
        
        Args:
            name: Phase name
            config: Phase configuration
        """
        self.name = name
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.processor = None
        
        # Initialize processor
        self._initialize_processor()
    
    def _initialize_processor(self) -> None:
        """Initialize the phase processor."""
        try:
            # Import processor class
            module_path, class_name = self.config.processor.rsplit('.', 1)
            module = importlib.import_module(module_path)
            processor_class = getattr(module, class_name)
            
            # Create processor instance
            self.processor = processor_class(config=self.config.dict())
            
        except Exception as e:
            self.logger.error(f"Error initializing processor for phase {self.name}: {str(e)}")
            raise
    
    async def process(self, file_path: Path, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process a file through this phase.
        
        Args:
            file_path: Path to the file to process
            context: Optional processing context
            
        Returns:
            ProcessingResult containing phase results
        """
        try:
            if not self.processor:
                raise ValueError(f"No processor initialized for phase {self.name}")
                
            # Process the file
            result = await self.processor.process(file_path, context)
            
            # Validate result
            if not result.success:
                self.logger.error(f"Phase {self.name} failed for {file_path}")
                
            return result
            
        except Exception as e:
            error_msg = f"Error in phase {self.name} for {file_path}: {str(e)}"
            self.logger.error(error_msg)
            return ProcessingResult(success=False, errors=[error_msg])
    
    async def cleanup(self) -> None:
        """Clean up phase resources."""
        try:
            if self.processor and hasattr(self.processor, 'cleanup'):
                await self.processor.cleanup()
        except Exception as e:
            self.logger.error(f"Error cleaning up phase {self.name}: {str(e)}") 