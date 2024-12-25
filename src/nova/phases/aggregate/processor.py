"""Markdown aggregate processor for Nova document processor."""

from pathlib import Path
from typing import Dict, Any, Optional, List
import os

from ...core.config import ProcessorConfig, PipelineConfig
from ...core.logging import get_logger
from ...core.errors import ProcessorError
from ...core.file_ops import FileOperationsManager
from ...core.pipeline.base import BaseProcessor

logger = get_logger(__name__)

class MarkdownAggregateProcessor(BaseProcessor):
    """Processor for aggregating markdown files."""
    
    def __init__(self, processor_config: ProcessorConfig, pipeline_config: PipelineConfig):
        """Initialize markdown aggregate processor.
        
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
            # Get input files from consolidate phase's output directory
            consolidate_dir = os.getenv('NOVA_PHASE_MARKDOWN_CONSOLIDATE')
            if not consolidate_dir:
                logger.error("NOVA_PHASE_MARKDOWN_CONSOLIDATE environment variable not set")
                return False
                
            input_files = list(Path(consolidate_dir).glob('**/*.md'))
            if not input_files:
                logger.warning("No markdown files found to process")
                return True
                
            # Create output file
            output_file = Path(self.output_dir) / "all_merged_markdown.md"
            
            # Process each file
            with output_file.open('w', encoding='utf-8') as out:
                # Add summary section marker
                out.write("--==SUMMARY==--\n\n")
                
                # Write summary content
                for input_file in input_files:
                    try:
                        # Read input file
                        content = input_file.read_text(encoding='utf-8')
                        
                        # Add file markers
                        out.write(f"<!-- START_FILE: {input_file.name} -->\n")
                        out.write(content)
                        out.write(f"\n<!-- END_FILE: {input_file.name} -->\n")
                        out.write("\n---\n\n")
                    except Exception as e:
                        logger.error(f"Error processing file {input_file}: {str(e)}")
                        continue
                
                # Add raw notes section marker
                out.write("\n--==RAW_NOTES==--\n\n")
                
                # Write raw notes content (same content for now)
                for input_file in input_files:
                    try:
                        content = input_file.read_text(encoding='utf-8')
                        out.write(f"<!-- START_FILE: {input_file.name} -->\n")
                        out.write(content)
                        out.write(f"\n<!-- END_FILE: {input_file.name} -->\n")
                        out.write("\n---\n\n")
                    except Exception as e:
                        logger.error(f"Error processing file {input_file}: {str(e)}")
                        continue
                
                # Add attachments section marker
                out.write("\n--==ATTACHMENTS==--\n\n")
                
                # Write attachments content (empty for now)
                out.write("No attachments yet\n")
                
            return True
        except Exception as e:
            logger.error(f"Error in MarkdownAggregateProcessor: {str(e)}")
            return False
            
    async def cleanup(self) -> None:
        """Clean up processor."""
        pass