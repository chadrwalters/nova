"""Base handler for pipeline processors."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from nova.core.pipeline.errors import ValidationError
from nova.core.models.result import ProcessingResult


class BaseHandler:
    """Base class for pipeline handlers."""

    def __init__(self):
        """Initialize base handler."""
        self.monitoring = None
        self.timing = None
        self.state = None

    def can_handle(self, file_path: Path) -> bool:
        """Check if handler can process a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if handler can process file
        """
        return False

    def process(self, input_file: Path, output_dir: Path) -> ProcessingResult:
        """Process a file.
        
        Args:
            input_file: Input file path
            output_dir: Output directory path
            
        Returns:
            Processing result
            
        Raises:
            ValidationError: If validation fails
            ProcessingError: If processing fails
        """
        raise NotImplementedError("Subclasses must implement process()")

    def validate(self, input_file: Path) -> None:
        """Validate input file.
        
        Args:
            input_file: Input file path
            
        Raises:
            ValidationError: If validation fails
        """
        if not input_file.exists():
            raise ValidationError(f"Input file does not exist: {input_file}")
        if not input_file.is_file():
            raise ValidationError(f"Input path is not a file: {input_file}")

    def validate_output_dir(self, output_dir: Path) -> None:
        """Validate output directory.
        
        Args:
            output_dir: Output directory path
            
        Raises:
            ValidationError: If validation fails
        """
        if not output_dir.exists():
            output_dir.mkdir(parents=True)
        elif not output_dir.is_dir():
            raise ValidationError(f"Output path is not a directory: {output_dir}")

    def get_output_path(self, input_file: Path, output_dir: Path) -> Path:
        """Get output path for input file.
        
        Args:
            input_file: Input file path
            output_dir: Output directory path
            
        Returns:
            Output file path
        """
        return output_dir / input_file.name 