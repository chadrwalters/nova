"""Error handling phase."""

from pathlib import Path
from typing import List, Optional, Dict, Any

from nova.core.pipeline.base_phase import PipelinePhase
from nova.core.errors import ValidationError, ProcessingError
from nova.core.models.result import ProcessingResult


class ErrorPhase(PipelinePhase):
    """Phase for handling errors."""
    
    def __init__(self, name: str, config: Dict[str, Any], output_dir: Path):
        """Initialize error phase.
        
        Args:
            name: Phase name
            config: Phase configuration
            output_dir: Output directory
        """
        super().__init__(name, config, output_dir)
        self.retry_count = 0
        self.max_retries = config.get("max_retries", 3)
        self.fail_validation = config.get("fail_validation", False)
        self.fail_processing = config.get("fail_processing", False)
        
    def validate_input(self, input_files: List[Path]) -> None:
        """Validate input files.
        
        Args:
            input_files: List of input files
            
        Raises:
            ValidationError: If validation fails
        """
        super().validate_input(input_files)
        
        if self.fail_validation:
            self.retry_count += 1
            if self.retry_count <= self.max_retries:
                raise ValidationError(f"Simulated validation error (attempt {self.retry_count}/{self.max_retries})")
            
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
                    
        except ValidationError as e:
            # Log error and fail phase
            self.logger.error(f"Phase {self.name} validation failed: {e}")
            result.add_error(str(e))
            raise ProcessingError(str(e))
            
        except Exception as e:
            # Log error and fail phase
            self.logger.error(f"Phase {self.name} failed: {e}")
            result.add_error(str(e))
            raise ProcessingError(str(e))
            
        return result
        
    def _process_file(self, input_file: Path, result: ProcessingResult) -> None:
        """Process a single file.
        
        Args:
            input_file: Input file path
            result: Processing result to update
            
        Raises:
            ProcessingError: If processing fails
        """
        if self.fail_processing:
            raise ProcessingError("Simulated processing error")
            
        result.add_processed_file(input_file)
        
    def cleanup(self) -> None:
        """Clean up phase resources."""
        super().cleanup()
        self.retry_count = 0 