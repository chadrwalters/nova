"""Parse phase module."""

import logging
from pathlib import Path
from typing import Optional
import traceback

from nova.core.metadata import FileMetadata
from nova.handlers.registry import HandlerRegistry
from nova.phases.base import Phase
from nova.utils.output_manager import OutputManager

logger = logging.getLogger(__name__)

class ParsePhase(Phase):
    """Phase that parses input files into a common format."""
    
    def __init__(self, pipeline, handler_registry: Optional[HandlerRegistry] = None):
        """Initialize parse phase.
        
        Args:
            pipeline: Pipeline instance this phase belongs to
            handler_registry: Optional handler registry. If not provided, will create one.
        """
        super().__init__(pipeline)
        self.handler_registry = handler_registry or HandlerRegistry(pipeline.config)
        self.output_manager = OutputManager(pipeline.config)
        
    def _get_handler(self, file_path: Path):
        """Get appropriate handler for file."""
        return self.handler_registry.get_handler(file_path)
        
    async def process(self, file_path: Path, output_dir: Path, metadata: Optional[FileMetadata] = None) -> Optional[FileMetadata]:
        """Process a file.
        
        Args:
            file_path: Path to file to process
            output_dir: Directory to write output files to
            metadata: Optional metadata from previous phase
            
        Returns:
            Metadata about processed file, or None if file was skipped
        """
        # Get output path for this file
        output_path = self.output_manager.get_output_path_for_phase(
            file_path,
            "parse",
            ".parsed.md"
        )
        return await self.process_file(file_path, output_path.parent)
        
    async def process_file(self, file_path: Path, output_dir: Path) -> Optional[FileMetadata]:
        """Process a single file through the parse phase."""
        try:
            # Get handler for file
            handler = self.handler_registry.get_handler(file_path)
            if handler is None:
                logger.debug(f"No handler found for {file_path}")
                self.pipeline.state['parse']['skipped_files'].add(file_path)
                return None
            
            # Process file
            metadata = await handler.process(file_path, output_dir)
            
            # Update pipeline state
            if metadata is None:
                self.pipeline.state['parse']['failed_files'].add(file_path)
            elif metadata.unchanged:
                self.pipeline.state['parse']['unchanged_files'].add(file_path)
            else:
                self.pipeline.state['parse']['successful_files'].add(file_path)
                if metadata.reprocessed:
                    self.pipeline.state['parse']['reprocessed_files'].add(file_path)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to process file: {file_path}")
            logger.error(traceback.format_exc())
            self.pipeline.state['parse']['failed_files'].add(file_path)
            return None