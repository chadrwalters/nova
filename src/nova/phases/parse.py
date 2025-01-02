"""Parse phase of the Nova pipeline."""

import json
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
        
        # Set up debug logging
        self.logger.setLevel(logging.DEBUG)

    def _save_metadata(self, file_path: Path, metadata: FileMetadata):
        """Save metadata to a file.
        
        Args:
            file_path: Path to the parsed file
            metadata: Metadata to save
        """
        try:
            # Get metadata file path using output manager
            metadata_path = self.pipeline.output_manager.get_output_path_for_phase(
                file_path,
                "parse",
                ".metadata.json"
            )
            
            # Convert metadata to dictionary
            metadata_dict = metadata.to_dict() if hasattr(metadata, 'to_dict') else metadata.__dict__
            
            # Write metadata to file
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata_dict, f, indent=2, default=str)
            
            self.logger.debug(f"Saved metadata for {file_path} to {metadata_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save metadata for {file_path}: {str(e)}")
            raise

    def _track_attachment(self, file_path: Path, parent_dir: str) -> None:
        """Track an attachment in the pipeline state.
        
        Args:
            file_path: Path to the attachment file
            parent_dir: Parent directory name
        """
        if parent_dir not in self.pipeline.state['parse']['attachments']:
            self.pipeline.state['parse']['attachments'][parent_dir] = []
            
        # Create attachment info
        attachment = {
            'path': str(file_path),
            'id': file_path.name,
            'content': None  # Content will be read in split phase
        }
        
        self.pipeline.state['parse']['attachments'][parent_dir].append(attachment)

    async def process_impl(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: Optional[FileMetadata] = None
    ) -> Optional[FileMetadata]:
        """Process a file in the parse phase.
        
        Args:
            file_path: Path to file to process
            output_dir: Directory to write output files to
            metadata: Optional metadata from previous phase
            
        Returns:
            Metadata about processed file, or None if file was skipped
        """
        try:
            # Get handler for file
            handler = self.handler_registry.get_handler(file_path)
            if handler is None:
                self.logger.warning(f"No handler found for {file_path}")
                self.pipeline.state['parse']['skipped_files'].add(file_path)
                self._update_file_stats(file_path, 'skipped')
                return None
                
            # Check if this is an attachment (file in a subdirectory)
            if len(file_path.relative_to(self.pipeline.config.input_dir).parts) > 1:
                parent_dir = file_path.parent.name
                self._track_attachment(file_path, parent_dir)
                
            # Initialize metadata if not provided
            if metadata is None:
                metadata = FileMetadata.from_file(
                    file_path=file_path,
                    handler_name=handler.name,
                    handler_version=handler.version
                )
            
            # Process file with handler
            try:
                metadata = await handler.process_impl(file_path, metadata)
            except Exception as e:
                self.logger.error(f"Handler failed to process {file_path}: {str(e)}")
                if metadata:
                    metadata.add_error(handler.name, str(e))
                    metadata.processed = False
                return metadata
            
            # Update pipeline state and stats
            if metadata is None:
                self.logger.error(f"Processing failed for {file_path}")
                self.pipeline.state['parse']['failed_files'].add(file_path)
                self._update_file_stats(file_path, 'failed', handler.name)
            elif metadata.unchanged:
                self.logger.debug(f"File unchanged: {file_path}")
                self.pipeline.state['parse']['unchanged_files'].add(file_path)
                self._update_file_stats(file_path, 'unchanged', handler.name)
            else:
                self.logger.info(f"Successfully processed {file_path}")
                self.pipeline.state['parse']['successful_files'].add(file_path)
                self._update_file_stats(file_path, 'successful', handler.name)
                if metadata.reprocessed:
                    self.logger.debug(f"File was reprocessed: {file_path}")
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
        
        self.logger.debug(f"Updated stats for {ext}: {status} (handler: {handler_name})")

    def finalize(self):
        """Finalize the parse phase."""
        # Print summary of file processing
        stats = self.pipeline.state['parse']['file_type_stats']
        self.logger.info("=== Parse Phase Summary ===")
        for ext, ext_stats in stats.items():
            self.logger.info(f"\nFile type: {ext}")
            self.logger.info(f"Total files: {ext_stats['total']}")
            self.logger.info(f"Successful: {ext_stats['successful']}")
            self.logger.info(f"Failed: {ext_stats['failed']}")
            self.logger.info(f"Skipped: {ext_stats['skipped']}")
            self.logger.info(f"Unchanged: {ext_stats['unchanged']}")
            self.logger.info(f"Handlers: {', '.join(ext_stats['handlers'])}")
        
        # Log any failed files
        failed_files = self.pipeline.state['parse']['failed_files']
        if failed_files:
            self.logger.error(f"\nFailed to process {len(failed_files)} files:")
            for file_path in failed_files:
                self.logger.error(f"  - {file_path}")
        
        # Log any skipped files
        skipped_files = self.pipeline.state['parse']['skipped_files']
        if skipped_files:
            self.logger.warning(f"\nSkipped {len(skipped_files)} files:")
            for file_path in skipped_files:
                self.logger.warning(f"  - {file_path}")