"""Parse phase of the Nova pipeline."""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Union
import traceback

from ..config.manager import ConfigManager
from ..models.document import DocumentMetadata
from .base import Phase
from nova.core.metadata import FileMetadata
from nova.handlers.registry import HandlerRegistry

logger = logging.getLogger(__name__)

class ParsePhase(Phase):
    """Phase that parses input files into a common format."""
    
    def __init__(self, pipeline):
        """Initialize the parse phase.
        
        Args:
            pipeline: Pipeline instance
        """
        super().__init__(pipeline)
        self.handler_registry = HandlerRegistry(pipeline.config)
        
        # Initialize state
        self.pipeline.state['parse'] = {
            'successful_files': set(),
            'failed_files': set(),
            'skipped_files': set(),
            'unchanged_files': set(),
            'reprocessed_files': set(),
            'file_type_stats': {}
        }
        
    async def process_impl(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: Optional[FileMetadata] = None
    ) -> Optional[FileMetadata]:
        """Process a file through the parse phase.
        
        Args:
            file_path: Path to file to process
            output_dir: Directory to write output files to
            metadata: Optional metadata from previous phase
            
        Returns:
            Document metadata if successful, None otherwise
        """
        try:
            # Initialize metadata if not provided
            if metadata is None:
                metadata = FileMetadata(file_path)
            
            # Get handler for file
            handler = self.handler_registry.get_handler(file_path)
            if handler is None:
                self.pipeline.state['parse']['skipped_files'].add(file_path)
                self._update_file_stats(file_path, 'skipped')
                return None
            
            # Process file
            metadata = await handler.process_impl(file_path, metadata)
            
            # Update pipeline state and stats
            if metadata is None:
                self.pipeline.state['parse']['failed_files'].add(file_path)
                self._update_file_stats(file_path, 'failed', handler.name)
            elif metadata.unchanged:
                self.pipeline.state['parse']['unchanged_files'].add(file_path)
                self._update_file_stats(file_path, 'unchanged', handler.name)
            else:
                self.pipeline.state['parse']['successful_files'].add(file_path)
                self._update_file_stats(file_path, 'successful', handler.name)
                if metadata.reprocessed:
                    self.pipeline.state['parse']['reprocessed_files'].add(file_path)
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to process file: {file_path}")
            self.logger.error(traceback.format_exc())
            if metadata:
                metadata.add_error("ParsePhase", str(e))
                metadata.processed = False
                return metadata
            return None
            
    def _update_file_stats(self, file_path: Path, status: str, handler_name: str = None):
        """Update file type statistics.
        
        Args:
            file_path: Path to file
            status: Status of processing ('successful', 'failed', 'skipped', 'unchanged')
            handler_name: Name of handler used to process file
        """
        # Get file extension
        ext = file_path.suffix.lower()
        if not ext:
            ext = 'no_extension'
        
        # Initialize stats for extension if needed
        if ext not in self.pipeline.state['parse']['file_type_stats']:
            self.pipeline.state['parse']['file_type_stats'][ext] = {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'skipped': 0,
                'unchanged': 0,
                'handlers': set()
            }
        
        # Update stats
        stats = self.pipeline.state['parse']['file_type_stats'][ext]
        stats['total'] += 1
        stats[status] += 1
        if handler_name:
            stats['handlers'].add(handler_name)

    def finalize(self):
        """Finalize the parse phase."""
        # Nothing to do in finalize for parse phase
        pass