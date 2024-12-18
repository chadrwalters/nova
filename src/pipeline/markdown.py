from pathlib import Path
import asyncio
import aiofiles
from typing import List, Optional
from ..core.config import NovaConfig
from ..core.logging import get_logger
from ..core.errors import ProcessingError, ErrorSeverity
from ..core.processor import process_markdown_file
from markdown_it import MarkdownIt

logger = get_logger(__name__)

async def process_markdown_files(config: NovaConfig) -> bool:
    """Process markdown files through the pipeline."""
    try:
        input_dir = config.processing.input_dir
        output_dir = config.processing.phase_markdown_parse
        
        # Ensure directories exist
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get list of markdown files
        markdown_files = list(input_dir.glob("*.md"))
        if not markdown_files:
            logger.warning("no_markdown_files_found", input_dir=str(input_dir))
            return False
            
        logger.info("processing_markdown_files",
                   file_count=len(markdown_files),
                   input_dir=str(input_dir))
        
        # Process each file
        tasks = []
        for file in markdown_files:
            tasks.append(process_markdown_file(file, output_dir, config))
            
        # Wait for all files to be processed
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for errors
        success = True
        for file, result in zip(markdown_files, results):
            if isinstance(result, Exception):
                logger.error("file_processing_failed",
                           file=str(file),
                           error=str(result))
                success = False
                
        return success
        
    except Exception as e:
        logger.error("markdown_processing_failed", error=str(e))
        return False