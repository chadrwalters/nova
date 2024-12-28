"""Markdown handler for parsing markdown files."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from nova.core.errors import ValidationError
from nova.phases.core.base_handler import BaseHandler, HandlerResult


class MarkdownHandler(BaseHandler):
    """Handler for parsing markdown files."""

    def __init__(
        self,
        name: str,
        options: Dict[str, Any],
        timing: Optional[Any] = None,
        metrics: Optional[Any] = None,
        monitoring: Optional[Any] = None,
        console: Optional[Any] = None
    ):
        """Initialize markdown handler.
        
        Args:
            name: Handler name
            options: Handler options
            timing: Optional timing manager
            metrics: Optional metrics tracker
            monitoring: Optional monitoring manager
            console: Optional console logger
        """
        super().__init__(options)
        self.name = name
        self.timing = timing
        self.metrics = metrics
        self.monitoring = monitoring
        self.console = console
        self.logger = logging.getLogger(__name__)

    def can_handle(self, file_path: Path, attachments: Optional[List[Path]] = None) -> bool:
        """Check if handler can process the file.
        
        Args:
            file_path: Path to the file
            attachments: Optional list of attachment paths
            
        Returns:
            True if handler can process the file, False otherwise
        """
        return file_path.suffix.lower() == '.md'

    async def process(
        self,
        file_path: Path,
        context: Dict[str, Any],
        attachments: Optional[List[Path]] = None
    ) -> HandlerResult:
        """Process markdown file.
        
        Args:
            file_path: Path to the file
            context: Processing context
            attachments: Optional list of attachment paths
            
        Returns:
            HandlerResult containing the processing outcome
            
        Raises:
            ValidationError: If processing fails
        """
        try:
            self.logger.info(f"Processing file: {file_path}")

            # Initialize result
            result = HandlerResult()

            # Read file content
            content = file_path.read_text()

            # Process content
            processed_content = self._process_content(content)

            # Update result
            result.content = processed_content
            result.processed_files.append(file_path)
            if attachments:
                result.processed_attachments.extend(attachments)

            self.logger.info(f"File processed successfully: {file_path}")
            return result

        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {str(e)}")
            raise ValidationError(f"Error processing file {file_path}: {str(e)}")

    def validate_output(self, result: HandlerResult) -> bool:
        """Validate handler output.
        
        Args:
            result: HandlerResult to validate
            
        Returns:
            True if output is valid, False otherwise
        """
        try:
            # Validate content
            if not result.content:
                self.logger.error("Empty content in handler result")
                return False

            # Validate processed files
            if not result.processed_files:
                self.logger.error("No processed files in handler result")
                return False

            # Validate file extensions
            for file in result.processed_files:
                if file.suffix.lower() != '.md':
                    self.logger.error(f"Invalid file extension: {file}")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating output: {str(e)}")
            return False

    def _process_content(self, content: str) -> str:
        """Process markdown content.
        
        Args:
            content: Content to process
            
        Returns:
            Processed content
        """
        try:
            # Add processing logic here
            # For now, just return the content as is
            return content

        except Exception as e:
            self.logger.error(f"Error processing content: {str(e)}")
            raise ValidationError(f"Error processing content: {str(e)}")

    async def cleanup(self):
        """Clean up handler resources."""
        try:
            # Clean up base handler
            await super().cleanup()

        except Exception as e:
            self.logger.error(f"Error cleaning up handler: {str(e)}")

    def get_name(self) -> str:
        """Get handler name.
        
        Returns:
            Handler name
        """
        return self.name

    def get_options(self) -> Dict[str, Any]:
        """Get handler options.
        
        Returns:
            Handler options dictionary
        """
        return self.config 