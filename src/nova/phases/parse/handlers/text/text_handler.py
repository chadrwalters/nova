"""Handler for processing text files."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import shutil
import os
import magic

from .....core.base_handler import BaseHandler
from .....core.models.result import ProcessingResult


class TextHandler(BaseHandler):
    """Handler for processing text files."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the handler.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        
        # Initialize supported formats
        self.supported_formats = {
            'text/plain',
            'text/markdown',
            'text/x-python',
            'text/x-java',
            'text/x-c',
            'text/x-c++',
            'text/x-script.python'
        }
        
        # Initialize metrics
        self.monitoring.set_threshold("memory_percent", 85.0)
    
    async def can_handle(self, file_path: Path) -> bool:
        """Check if this handler can process the file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if this handler can process the file, False otherwise
        """
        try:
            mime_type = magic.from_file(str(file_path), mime=True)
            self.state.add_metric("mime_type", mime_type)
            return mime_type in self.supported_formats
        except Exception as e:
            self.monitoring.record_error(f"Error checking file type: {str(e)}")
            return False
    
    async def _process_impl(self, file_path: Path, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process a text file.
        
        Args:
            file_path: Path to the file to process
            context: Optional processing context
            
        Returns:
            ProcessingResult containing processed content and metadata
        """
        try:
            async with self.monitoring.async_monitor_operation("copy_file"):
                # Monitor resource usage
                usage = self.monitoring.capture_resource_usage()
                self.monitoring._check_thresholds(usage)
                
                # Create output path
                output_path = Path(self.config["output_dir"]) / file_path.name
                
                # Copy file to output directory
                shutil.copy2(file_path, output_path)
                
                # Record file size
                file_size = file_path.stat().st_size
                self.state.add_metric("file_size", file_size)
            
            async with self.monitoring.async_monitor_operation("extract_metadata"):
                # Extract metadata
                metadata = await self._extract_metadata(file_path)
                
                # Record metadata in state
                for key, value in metadata.items():
                    self.state.add_metric(f"metadata_{key}", value)
            
            # Create result
            result = ProcessingResult(
                success=True,
                content=str(output_path),
                metadata={
                    **metadata,
                    'metrics': self.state.metrics
                }
            )
            result.add_processed_file(file_path)
            result.add_processed_file(output_path)
            
            # Record success
            self.monitoring.increment_counter("files_processed")
            self.state.add_processed_file(output_path)
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            self.monitoring.record_error(error_msg)
            self.state.add_error(error_msg)
            self.state.add_failed_file(file_path)
            return ProcessingResult(success=False, errors=[error_msg])
    
    async def _extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from a text file.
        
        Args:
            file_path: Path to the text file
            
        Returns:
            Dictionary of text metadata
        """
        metadata = {
            'mime_type': None,
            'size': None,
            'original_path': str(file_path),
            'encoding': None,
            'line_count': None
        }
        
        try:
            # Get basic metadata
            metadata.update({
                'mime_type': magic.from_file(str(file_path), mime=True),
                'size': os.path.getsize(file_path)
            })
            
            # Get encoding and line count
            with open(file_path, 'rb') as f:
                content = f.read()
                try:
                    content.decode('utf-8')
                    metadata['encoding'] = 'utf-8'
                except UnicodeDecodeError:
                    metadata['encoding'] = 'unknown'
                
                metadata['line_count'] = len(content.splitlines())
                
        except Exception as e:
            error_msg = f"Error extracting metadata from {file_path}: {str(e)}"
            self.monitoring.record_error(error_msg)
            self.state.add_error(error_msg)
        
        return metadata
    
    def validate(self, result: ProcessingResult) -> bool:
        """Validate the processing results.
        
        Args:
            result: The ProcessingResult to validate
            
        Returns:
            True if results are valid, False otherwise
        """
        if not result.success or not result.content:
            error_msg = "Invalid processing result"
            self.monitoring.record_error(error_msg)
            self.state.add_error(error_msg)
            return False
        return True
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Clean up any created files
            for file_path in self.state.processed_files:
                try:
                    if file_path.exists():
                        file_path.unlink()
                except Exception as e:
                    error_msg = f"Error cleaning up file {file_path}: {str(e)}"
                    self.monitoring.record_error(error_msg)
                    self.state.add_error(error_msg)
        finally:
            await super().cleanup() 