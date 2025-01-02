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
        
        # Initialize state
        self.pipeline.state['parse'] = {
            'successful_files': set(),
            'failed_files': set(),
            'skipped_files': set(),
            'unchanged_files': set(),
            'reprocessed_files': set(),
            'file_type_stats': {}
        }
        
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
            self.logger.debug(f"Starting to process file: {file_path}")
            
            # Initialize metadata if not provided
            if metadata is None:
                metadata = FileMetadata(file_path)
                self.logger.debug(f"Created new metadata for {file_path}")
            
            # Get handler for file
            handler = self.handler_registry.get_handler(file_path)
            if handler is None:
                self.logger.warning(f"No handler found for file type: {file_path.suffix}")
                self.pipeline.state['parse']['skipped_files'].add(file_path)
                self._update_file_stats(file_path, 'skipped')
                return None
            
            self.logger.debug(f"Using handler {handler.name} for {file_path}")
            
            # Process file
            metadata = await handler.process_impl(file_path, metadata)
            
            # Save metadata file if processing was successful
            if metadata is not None and not metadata.unchanged:
                # Create output directory structure
                relative_path = file_path.relative_to(self.pipeline.config.input_dir)
                output_path = output_dir / relative_path.parent
                output_path.mkdir(parents=True, exist_ok=True)
                
                # Create parsed file path
                parsed_file_name = file_path.stem + '.parsed.md'
                parsed_file_path = output_path / parsed_file_name
                self._save_metadata(parsed_file_path, metadata)
                self.logger.debug(f"Created parsed file: {parsed_file_path}")
            
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