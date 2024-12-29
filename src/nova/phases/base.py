"""Base phase module."""

from pathlib import Path
from typing import Optional
import logging
import shutil

from nova.core.metadata import FileMetadata
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
        
    async def process_file(self, file_path: Path, output_dir: Path) -> Optional[FileMetadata]:
        """Process a single file through this phase.
        
        Args:
            file_path: Path to file to process
            output_dir: Directory to write output files to
            
        Returns:
            Metadata about processed file, or None if file was skipped
        """
        try:
            # Create output directory if needed
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Get relative path from input directory to maintain directory structure
            rel_path = file_path.relative_to(self.pipeline.config.input_dir)
            output_path = output_dir / rel_path.parent / f"{rel_path.stem}.parsed.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Process content
            content = await self._process_content(file_path)
            
            # Write output file
            was_written = self._safe_write_file(output_path, content)
            
            # Create metadata
            metadata = FileMetadata(file_path)
            metadata.processed = True
            metadata.unchanged = not was_written
            metadata.add_output_file(output_path)
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to process file {file_path}: {str(e)}")
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