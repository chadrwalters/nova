"""Base phase module."""

from pathlib import Path
from typing import Optional
import logging
import shutil
import traceback

from nova.models.document import DocumentMetadata
from nova.utils.file_utils import safe_write_file

class Phase:
    """Base class for pipeline phases."""
    
    def __init__(self, pipeline):
        """Initialize phase.
        
        Args:
            pipeline: Pipeline instance this phase belongs to
        """
        self.pipeline = pipeline
        # Use the actual class's module name for logging
        self.logger = logging.getLogger(self.__class__.__module__)
        
    async def process_file(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: Optional[DocumentMetadata] = None
    ) -> Optional[DocumentMetadata]:
        """Process a file.
        
        Args:
            file_path: Path to file to process
            output_dir: Directory to write output files to
            metadata: Optional metadata from previous phase
            
        Returns:
            Metadata about processed file, or None if file was skipped
        """
        try:
            # Initialize metadata if not provided
            if metadata is None:
                metadata = DocumentMetadata.from_file(
                    file_path=file_path,
                    handler_name=self.__class__.__name__,
                    handler_version="1.0"
                )
            
            # Process the file
            metadata = await self.process_impl(file_path, output_dir, metadata)
            if metadata:
                return metadata
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to process file: {file_path}")
            self.logger.error(traceback.format_exc())
            if metadata:
                metadata.add_error(self.__class__.__name__, str(e))
                metadata.processed = False
                return metadata
            return None

    def _safe_write_file(self, file_path: Path, content: str, encoding: str = 'utf-8') -> bool:
        """Write content to file only if it has changed.
        
        Args:
            file_path: Path to file.
            content: Content to write.
            encoding: File encoding.
            
        Returns:
            True if file was written, False if unchanged.
        """
        return safe_write_file(file_path, content, encoding) 