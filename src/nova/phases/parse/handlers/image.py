"""Handler for image files."""

# Standard library imports
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Third-party imports
import magic

# Nova package imports
from nova.core.base_handler import BaseHandler
from nova.core.models.result import ProcessingResult
from nova.core.utils.metrics import MetricsTracker
from nova.core.utils.timing import TimingManager


class ImageHandler(BaseHandler):
    """Handler for image files."""
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        timing: Optional[TimingManager] = None,
        metrics: Optional[MetricsTracker] = None
    ):
        """Initialize the handler.
        
        Args:
            config: Handler configuration
            timing: Optional timing utility
            metrics: Optional metrics tracker
        """
        config = config or {}
        super().__init__(config, timing, metrics)
        self.supported_formats = {
            'image/png',
            'image/jpeg',
            'image/gif',
            'image/webp',
            'image/heic'
        }
        self.output_dir = config.get('output_dir')
        if not self.output_dir:
            raise ValueError("output_dir is required in config")
        
    async def can_handle(self, file_path: str) -> bool:
        """Check if the handler can process the file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if the handler can process the file
        """
        try:
            mime_type = magic.from_file(file_path, mime=True)
            self.state.metrics['mime_type'] = mime_type
            return mime_type in self.supported_formats
        except Exception as e:
            self.logger.error(f"Error checking file type: {str(e)}")
            return False
            
    async def process(self, file_path: str, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process an image file.
        
        Args:
            file_path: Path to the file to process
            context: Optional processing context
            
        Returns:
            ProcessingResult containing processing results
        """
        try:
            # Verify file exists
            if not os.path.exists(file_path):
                return ProcessingResult(
                    success=False,
                    errors=[f"File not found: {file_path}"]
                )
                
            # Verify output directory exists
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
                
            # Process image
            async with self.monitoring.async_monitor_operation("process_image"):
                # Copy image to output directory
                output_path = Path(self.output_dir) / Path(file_path).name
                with open(file_path, 'rb') as src, open(output_path, 'wb') as dst:
                    dst.write(src.read())
                    
                # Extract metadata
                mime_type = self.state.get('mime_type')
                metadata = {
                    'mime_type': mime_type,
                    'size': os.path.getsize(file_path),
                    'filename': Path(file_path).name
                }
                
                return ProcessingResult(
                    success=True,
                    processed_files=[Path(output_path)],
                    metadata=metadata,
                    content=str(output_path)
                )
                
        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            self.logger.error(error_msg)
            return ProcessingResult(
                success=False,
                errors=[error_msg]
            )
            
    def validate(self, result: ProcessingResult) -> bool:
        """Validate processing result.
        
        Args:
            result: Processing result to validate
            
        Returns:
            True if result is valid
        """
        if not result.success:
            self.monitoring.increment_counter("errors")
            return False
            
        if not result.processed_files:
            self.monitoring.increment_counter("errors")
            self.logger.error("No processed files in result")
            return False
            
        for file_path in result.processed_files:
            if not os.path.exists(file_path):
                self.monitoring.increment_counter("errors")
                self.logger.error(f"Processed file not found: {file_path}")
                return False
                
        return True
            
    def cleanup(self) -> None:
        """Clean up resources."""
        pass 