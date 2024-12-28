"""Handler for processing file attachments."""

# Standard library imports
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

# Nova package imports
from nova.core.handlers.base import BaseHandler
from nova.core.models.result import ProcessingResult


class AttachmentProcessor(BaseHandler):
    """Handler for processing file attachments."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the handler.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        
        # Get required configuration
        if not config:
            raise ValueError("Configuration must be provided")
            
        # Get required paths
        self.output_dir = str(Path(config.get('output_dir', '')))
        if not self.output_dir:
            raise ValueError("output_dir must be specified in configuration")
            
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
    
    async def can_handle(self, file_path: Path) -> bool:
        """Check if this handler can process the file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if this handler can process the file, False otherwise
        """
        return file_path.is_file()
    
    async def process(self, file_path: Path, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process a file attachment.
        
        Args:
            file_path: Path to the file to process
            context: Optional processing context
            
        Returns:
            ProcessingResult containing processed content and metadata
        """
        try:
            # Create output path
            output_path = Path(self.output_dir) / file_path.name
            
            # Copy file to output directory
            shutil.copy2(file_path, output_path)
            
            # Create result
            result = ProcessingResult(
                success=True,
                content=str(output_path),
                metadata={'original_path': str(file_path)}
            )
            result.add_processed_file(output_path)
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            return ProcessingResult(success=False, errors=[error_msg])
    
    def validate_output(self, result: ProcessingResult) -> bool:
        """Validate the processing results.
        
        Args:
            result: The ProcessingResult to validate
            
        Returns:
            True if results are valid, False otherwise
        """
        return result.success and bool(result.content)
    
    async def rollback(self, result: ProcessingResult) -> None:
        """Roll back any changes made during processing.
        
        Args:
            result: The ProcessingResult to roll back
        """
        # Clean up any created files
        for file_path in result.processed_files:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                self.logger.error(f"Error cleaning up file {file_path}: {str(e)}") 