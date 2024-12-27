"""Text file handler."""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from nova.core.pipeline.base_handler import BaseHandler
from nova.core.pipeline.errors import ValidationError
from nova.core.pipeline.types import ProcessingResult


class TextHandler(BaseHandler):
    """Handler for text files."""

    def __init__(self, 
                 config: Optional[Dict[str, Any]] = None,
                 timing: bool = False,
                 **kwargs: Any):
        """Initialize text handler.
        
        Args:
            config: Handler configuration
            timing: Whether to track timing
            **kwargs: Additional arguments
        """
        super().__init__(config, **kwargs)
        self.timing = timing
        self.logger = logging.getLogger(__name__)

    def can_handle(self, file_path: Path) -> bool:
        """Check if handler can process file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Whether handler can process file
        """
        return file_path.suffix in ['.txt', '.md', '.py', '.js', '.css', '.html', '.json', '.yaml', '.yml']

    async def process(self, file_path: Path) -> ProcessingResult:
        """Process text file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Processing result
        """
        try:
            if not file_path.exists():
                return ProcessingResult(
                    success=False,
                    errors=[f"File not found: {file_path}"]
                )

            if not self.can_handle(file_path):
                return ProcessingResult(
                    success=False,
                    errors=[f"Unsupported file type: {file_path.suffix}"]
                )

            # Read file content
            content = file_path.read_text(encoding='utf-8')

            # Extract metadata
            metadata = self._extract_metadata(file_path)

            # Copy to output directory
            output_path = self._get_output_path(file_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding='utf-8')

            return ProcessingResult(
                success=True,
                processed_files=[output_path],
                metadata=metadata,
                content=content
            )

        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            self.logger.error(error_msg)
            return ProcessingResult(
                success=False,
                errors=[error_msg]
            )

    def _extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from file.
        
        Args:
            file_path: Path to file
            
        Returns:
            File metadata
        """
        return {
            'filename': file_path.name,
            'extension': file_path.suffix,
            'size': file_path.stat().st_size,
            'mime_type': self._get_mime_type(file_path)
        }

    def _get_mime_type(self, file_path: Path) -> str:
        """Get file MIME type.
        
        Args:
            file_path: Path to file
            
        Returns:
            MIME type
        """
        mime_types = {
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.py': 'text/x-python',
            '.js': 'application/javascript',
            '.css': 'text/css',
            '.html': 'text/html',
            '.json': 'application/json',
            '.yaml': 'application/x-yaml',
            '.yml': 'application/x-yaml'
        }
        return mime_types.get(file_path.suffix, 'text/plain')

    def _get_output_path(self, input_path: Path) -> Path:
        """Get output path for file.
        
        Args:
            input_path: Input file path
            
        Returns:
            Output file path
        """
        if not self.output_dir:
            raise ValidationError("output_dir is required in config")
        return Path(self.output_dir) / input_path.name

    def validate(self, result: ProcessingResult) -> bool:
        """Validate processing result.
        
        Args:
            result: Processing result
            
        Returns:
            Whether result is valid
        """
        if not result.success:
            return False

        if not result.processed_files:
            self.logger.error("No processed files in result")
            return False

        for file_path in result.processed_files:
            if not file_path.exists():
                self.logger.error(f"Output file not found: {file_path}")
                return False

        return True

    async def cleanup(self) -> None:
        """Clean up handler resources."""
        # Nothing to clean up for text handler
        pass 