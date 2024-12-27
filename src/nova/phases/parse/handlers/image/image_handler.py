"""Handler for processing image files."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import shutil
import os
from PIL import Image

from .....core.base_handler import BaseHandler
from .....core.models.result import ProcessingResult


class ImageHandler(BaseHandler):
    """Handler for processing image files."""
    
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
        
        # Initialize supported formats
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif'}
    
    async def can_handle(self, file_path: Path) -> bool:
        """Check if this handler can process the file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if this handler can process the file, False otherwise
        """
        return file_path.suffix.lower() in self.supported_formats
    
    async def process(self, file_path: Path, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process an image file.
        
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
            
            # Extract metadata
            metadata = self._extract_metadata(file_path)
            
            # Create result
            result = ProcessingResult(
                success=True,
                content=str(output_path),
                metadata=metadata
            )
            result.add_processed_file(output_path)
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            return ProcessingResult(success=False, errors=[error_msg])
    
    def _extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from an image file.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Dictionary of image metadata
        """
        metadata = {
            'format': None,
            'mode': None,
            'size': None,
            'original_path': str(file_path)
        }
        
        try:
            with Image.open(file_path) as img:
                metadata.update({
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size
                })
        except Exception as e:
            self.logger.error(f"Error extracting metadata from {file_path}: {str(e)}")
        
        return metadata
    
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