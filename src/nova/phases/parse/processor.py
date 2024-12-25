"""Markdown processor for Nova document processor."""

from pathlib import Path
from typing import Dict, Any, Optional, List
import os

from ...core.config import ProcessorConfig, PipelineConfig
from ...core.logging import get_logger
from ...core.errors import ProcessorError
from ...core.file_ops import FileOperationsManager
from ...core.pipeline.base import BaseProcessor

logger = get_logger(__name__)

class MarkdownProcessor(BaseProcessor):
    """Processor for markdown files."""
    
    def __init__(self, processor_config: ProcessorConfig, pipeline_config: PipelineConfig):
        """Initialize markdown processor.
        
        Args:
            processor_config: Processor configuration
            pipeline_config: Pipeline configuration
        """
        super().__init__(processor_config, pipeline_config)
        self.file_ops = FileOperationsManager()
        
    async def setup(self) -> None:
        """Set up processor."""
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def process(self) -> bool:
        """Process markdown files.
        
        Returns:
            True if processing completed successfully, False otherwise
        """
        try:
            # Get input files
            input_files = list(Path(self.pipeline_config.input_dir).glob('**/*.md'))
            if not input_files:
                logger.warning("No markdown files found to process")
                return True
                
            # Process each file
            for input_file in input_files:
                try:
                    await self._process_file(input_file)
                except Exception as e:
                    logger.error(f"Failed to process {input_file}: {str(e)}")
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"Error in markdown processor: {str(e)}")
            return False
            
    async def _process_file(self, input_file: Path) -> None:
        """Process a single markdown file.
        
        Args:
            input_file: Path to input file
            
        Raises:
            ProcessorError: If processing fails
        """
        # Read input file
        content = await self.file_ops.read_file(input_file)
        
        # Create output path preserving directory structure
        rel_path = input_file.relative_to(self.pipeline_config.input_dir)
        output_file = self.output_dir / rel_path
        
        # Create parent directories
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write processed content
        await self.file_ops.write_file(output_file, content)
        
    async def cleanup(self) -> None:
        """Clean up processor."""
        pass 