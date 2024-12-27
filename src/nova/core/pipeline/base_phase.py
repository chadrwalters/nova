"""Base phase implementation."""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from nova.core.errors import ValidationError, ProcessingError
from nova.core.models.result import ProcessingResult


class PipelinePhase:
    """Base class for pipeline phases."""
    
    def __init__(self, name: str, config: Dict[str, Any], output_dir: Path):
        """Initialize phase.
        
        Args:
            name: Phase name
            config: Phase configuration
            output_dir: Output directory
            
        Raises:
            ValidationError: If configuration is invalid
        """
        self.name = name
        self.config = config
        self.output_dir = output_dir
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
        # Validate configuration
        self._validate_config()
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _validate_config(self) -> None:
        """Validate phase configuration.
        
        Raises:
            ValidationError: If configuration is invalid
        """
        if not isinstance(self.config, dict):
            raise ValidationError("Invalid phase configuration")
            
        required_keys = ["processor", "components"]
        for key in required_keys:
            if key not in self.config:
                raise ValidationError(f"Missing required key: {key}")
                
    def validate_input(self, input_files: List[Path]) -> None:
        """Validate input files.
        
        Args:
            input_files: List of input files
            
        Raises:
            ValidationError: If input is invalid
        """
        if not input_files:
            raise ValidationError("No input files provided")
            
        for file_path in input_files:
            if not file_path.exists():
                raise ValidationError(f"Input file does not exist: {file_path}")
                
    def process(self, input_files: List[Path]) -> ProcessingResult:
        """Process input files.
        
        Args:
            input_files: List of input files
            
        Returns:
            Processing result
            
        Raises:
            ProcessingError: If processing fails
        """
        result = ProcessingResult()
        
        try:
            # Validate input
            self.validate_input(input_files)
            
            # Process files
            for input_file in input_files:
                try:
                    # Process file
                    self._process_file(input_file, result)
                    
                except Exception as e:
                    # Log error and continue
                    self.logger.error(f"Failed to process file {input_file}: {e}")
                    result.add_error(str(e))
                    result.add_failed_file(input_file)
                    
        except Exception as e:
            # Log error and fail phase
            self.logger.error(f"Phase {self.name} failed: {e}")
            result.add_error(str(e))
            raise ProcessingError(str(e))
            
        return result
        
    def _process_file(self, input_file: Path, result: ProcessingResult) -> None:
        """Process single file.
        
        Args:
            input_file: Input file
            result: Processing result to update
            
        Raises:
            ProcessingError: If processing fails
        """
        # Get processor
        processor = self.config["processor"]
        
        # Process file
        try:
            output_file = processor.process_file(input_file, self.output_dir)
            result.add_processed_file(input_file)
            result.add_output_file(output_file)
            
        except Exception as e:
            raise ProcessingError(f"Failed to process file {input_file}: {e}")
            
    def cleanup(self) -> None:
        """Clean up phase resources."""
        pass 