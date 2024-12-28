"""Office document handler for parsing office files."""

import os
from pathlib import Path
import shutil
import magic
from typing import Dict, Any, Optional

from nova.core.models.result import ProcessingResult
from nova.phases.core.base_handler import BaseHandler, HandlerResult
from nova.core.utils.metrics import MonitoringManager
from nova.core.models.state import HandlerState


class OfficeHandler(BaseHandler):
    """Handler for processing office documents."""
    
    SUPPORTED_MIME_TYPES = {
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ('word', 'docx'),
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': ('powerpoint', 'pptx'),
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ('excel', 'xlsx'),
        'application/pdf': ('pdf', 'pdf')
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the handler.
        
        Args:
            config: Handler configuration
        """
        super().__init__(config)
        self.output_dir = Path(config.get("output_dir")) if config else None
        self.monitoring = MonitoringManager()
        self.state = HandlerState()
    
    async def can_handle(self, file_path: Path) -> bool:
        """Check if the file can be handled.
        
        Args:
            file_path: Path to the file
            
        Returns:
            bool: True if the file can be handled
        """
        try:
            mime_type = magic.from_file(str(file_path), mime=True)
            self.state.metrics["mime_type"] = mime_type
            return mime_type in self.SUPPORTED_MIME_TYPES
        except Exception as e:
            self.state.errors.append(f"Error detecting file type: {str(e)}")
            self.monitoring.metrics["errors"] += 1
            return False
    
    async def process(self, file_path: Path) -> ProcessingResult:
        """Process the office document.
        
        Args:
            file_path: Path to the file
            
        Returns:
            ProcessingResult: Processing result
        """
        if not self.output_dir:
            error = "No output directory specified"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            return ProcessingResult(success=False, errors=[error])
        
        if not file_path.exists():
            error = f"File not found: {file_path}"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            self.state.failed_files.add(file_path)
            return ProcessingResult(success=False, errors=[error])
        
        try:
            # Start monitoring
            with self.monitoring.monitor_operation("process_office_file"):
                # Get file metadata
                mime_type = magic.from_file(str(file_path), mime=True)
                doc_type, format_type = self.SUPPORTED_MIME_TYPES.get(mime_type, (None, None))
                
                # Create output path
                output_file = self.output_dir / file_path.name
                
                # Copy file to output directory
                shutil.copy2(file_path, output_file)
                
                # Extract metadata
                metadata = {
                    "mime_type": mime_type,
                    "type": doc_type,
                    "format": format_type,
                    "original_path": str(file_path)
                }
                
                # Get file size
                try:
                    metadata["size"] = os.path.getsize(file_path)
                except Exception as e:
                    self.state.errors.append(f"Error getting file size: {str(e)}")
                    self.monitoring.metrics["errors"] += 1
                    metadata["size"] = None
                
                # Add metrics
                metrics = {
                    "file_size": metadata.get("size"),
                    "metadata_mime_type": metadata.get("mime_type"),
                    "metadata_size": metadata.get("size"),
                    "metadata_type": metadata.get("type"),
                    "metadata_format": metadata.get("format")
                }
                metadata["metrics"] = metrics
                
                # Update state
                self.state.processed_files.add(file_path)
                self.monitoring.metrics["files_processed"] += 1
                
                return ProcessingResult(
                    success=True,
                    content=str(output_file),
                    metadata=metadata
                )
                
        except Exception as e:
            error = f"Error processing file {file_path}: {str(e)}"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            self.state.failed_files.add(file_path)
            return ProcessingResult(success=False, errors=[error])
    
    def validate(self, result: ProcessingResult) -> bool:
        """Validate the processing result.
        
        Args:
            result: Processing result to validate
            
        Returns:
            bool: True if the result is valid
        """
        if not result.success:
            return False
            
        if not result.content:
            error = "No content in processing result"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            return False
            
        return True
    
    def validate_output(self, result: HandlerResult) -> bool:
        """Validate the processing results.
        
        Args:
            result: The HandlerResult to validate
            
        Returns:
            bool: True if results are valid
        """
        if not result.content:
            error = "No content in processing result"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            return False
            
        if not result.metadata:
            error = "No metadata in processing result"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            return False
            
        if not result.metadata.get("mime_type"):
            error = "No mime type in metadata"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            return False
            
        if not result.metadata.get("type"):
            error = "No document type in metadata"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            return False
            
        if not result.metadata.get("format"):
            error = "No format in metadata"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            return False
            
        return True
    
    async def cleanup(self):
        """Clean up resources."""
        try:
            # Clean up output files
            if self.output_dir and self.output_dir.exists():
                for file in self.output_dir.iterdir():
                    if file.is_file():
                        file.unlink()
            
            # Stop monitoring
            self.monitoring.stop()
            
            # Update state
            self.state.end_time = self.monitoring.state["end_time"]
            
        except Exception as e:
            error = f"Error during cleanup: {str(e)}"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1 