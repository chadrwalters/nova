"""Markdown split processor for Nova document processor."""

from pathlib import Path
from typing import Dict, Any, Optional
import os

from ...core.pipeline.base import BaseProcessor
from ...core.config import ProcessorConfig, PipelineConfig
from ...core.errors import ProcessorError
from ...core.logging import get_logger
from .handlers.split_handler import SplitHandler

logger = get_logger(__name__)

class ThreeFileSplitProcessor(BaseProcessor):
    """Processor for splitting aggregated markdown into three files."""
    
    def __init__(self, processor_config: ProcessorConfig, pipeline_config: PipelineConfig):
        super().__init__(processor_config, pipeline_config)
        self.handler = None
        logger.debug("ThreeFileSplitProcessor initialized")
        
    async def setup(self):
        """Set up the processor."""
        await super().setup()
        logger.debug("Starting ThreeFileSplitProcessor setup")
        
        # Get handler config from processor options
        handler_config = self.processor_config.options.get('handler', {})
        logger.debug(f"Handler config from options: {handler_config}")
        
        if not handler_config:
            # Use default config from pipeline.yaml with absolute paths
            output_dir = str(self.output_dir)
            logger.debug(f"Using default config with output_dir: {output_dir}")
            
            handler_config = {
                'output_files': {
                    'summary': str(Path(output_dir) / 'summary.md'),
                    'raw_notes': str(Path(output_dir) / 'raw_notes.md'),
                    'attachments': str(Path(output_dir) / 'attachments.md')
                },
                'section_markers': {
                    'summary': '--==SUMMARY==--',
                    'raw_notes': '--==RAW_NOTES==--',
                    'attachments': '--==ATTACHMENTS==--'
                }
            }
            logger.debug(f"Created default handler config: {handler_config}")
            
        try:
            self.handler = SplitHandler(handler_config)
            logger.debug("Created SplitHandler instance")
            await self.handler.setup()
            logger.debug("SplitHandler setup completed")
        except Exception as e:
            logger.error(f"Failed to initialize SplitHandler: {str(e)}")
            raise
        
    async def process(self) -> bool:
        """Process the aggregated markdown file."""
        try:
            # Get the aggregate phase's output directory from environment
            aggregate_dir = os.getenv('NOVA_PHASE_MARKDOWN_AGGREGATE')
            if not aggregate_dir:
                logger.error("NOVA_PHASE_MARKDOWN_AGGREGATE environment variable not set")
                return False
                
            # Look for the input file in the aggregate phase's output directory
            input_file = Path(aggregate_dir) / "all_merged_markdown.md"
            if not input_file.exists():
                logger.error(f"Aggregated markdown file not found: {input_file}")
                return False
                
            success = await self.handler.process_file(input_file)
            if not success:
                logger.error("Failed to process aggregated markdown file")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error in ThreeFileSplitProcessor: {str(e)}")
            return False
            
    async def cleanup(self):
        """Clean up resources."""
        if self.handler:
            await self.handler.cleanup()