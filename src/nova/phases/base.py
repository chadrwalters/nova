"""Base phase implementation."""
import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional, Set, Union

from nova.config.manager import ConfigManager
from nova.core.metadata import FileMetadata

logger = logging.getLogger(__name__)


class Phase:
    """Base class for pipeline phases."""
    
    def __init__(self, name: str, config: ConfigManager, pipeline=None):
        """Initialize phase.
        
        Args:
            name: Phase name
            config: Configuration manager
            pipeline: Optional pipeline instance
        """
        self.name = name
        self.config = config
        self.pipeline = pipeline
        self.lock = asyncio.Lock()
        self.processed_files: Set[Path] = set()
        self.failed_files: Dict[Path, str] = {}
        self.logger = logging.getLogger(self.__class__.__module__)
        
    async def process_file(self, file_path: Union[str, Path], output_dir: Union[str, Path]) -> Optional[FileMetadata]:
        """Process a single file.
        
        Args:
            file_path: Path to file to process
            output_dir: Directory to write output files to
            
        Returns:
            Optional metadata about processed file
        """
        file_path = Path(file_path)
        output_dir = Path(output_dir)
        
        try:
            # Skip if already processed
            if file_path in self.processed_files:
                self.logger.debug(f"Skipping already processed file: {file_path}")
                return None
            
            # Process file
            metadata = await self.process_impl(file_path, output_dir)
            
            # Mark as processed
            self.processed_files.add(file_path)
            
            return metadata
            
        except Exception as e:
            # Log error and add to failed files
            self.logger.error(f"Failed to process {file_path}: {str(e)}")
            self.failed_files[file_path] = str(e)
            raise
            
    async def process_impl(self, file_path: Path, output_dir: Path) -> Optional[FileMetadata]:
        """Process implementation to be overridden by subclasses.
        
        Args:
            file_path: Path to file to process
            output_dir: Directory to write output files to
            
        Returns:
            Optional metadata about processed file
        """
        raise NotImplementedError("Subclasses must implement process_impl")
        
    def finalize(self) -> None:
        """Finalize phase processing."""
        pass 