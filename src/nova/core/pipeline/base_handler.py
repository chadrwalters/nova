"""Base handler."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
from nova.core.pipeline.errors import ValidationError
from nova.core.pipeline.types import ProcessingResult


class BaseHandler:
    """Base class for pipeline handlers."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs: Any):
        """Initialize base handler.
        
        Args:
            config: Handler configuration
            **kwargs: Additional arguments
        """
        self.config = config or {}
        self.output_dir = self.config.get('output_dir')
        self.options = self.config.get('options', {})
        self.logger = logging.getLogger(__name__)

    def validate(self) -> None:
        """Validate handler configuration.
        
        Raises:
            ValidationError: If validation fails
        """
        if not self.output_dir:
            raise ValidationError("Output directory is required")

    def can_handle(self, file_path: Path) -> bool:
        """Check if handler can process file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Whether handler can process file
        """
        return False

    async def process(self, file_path: Path) -> ProcessingResult:
        """Process file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Processing result
        """
        try:
            # Validate configuration
            self.validate()

            # Check if handler can process file
            if not self.can_handle(file_path):
                return ProcessingResult(
                    success=False,
                    errors=[f"Handler cannot process file: {file_path}"]
                )

            # Process file
            return await self._process_file(file_path)

        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            self.logger.error(error_msg)
            return ProcessingResult(
                success=False,
                errors=[error_msg]
            )

    async def _process_file(self, file_path: Path) -> ProcessingResult:
        """Process a single file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Processing result
        """
        raise NotImplementedError("Subclasses must implement _process_file")

    async def cleanup(self) -> None:
        """Clean up handler resources."""
        pass 