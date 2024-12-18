from pathlib import Path
import asyncio
import aiofiles
from typing import List, Optional
from ..core.config import NovaConfig
from ..core.logging import get_logger
from ..core.errors import ProcessingError, ErrorSeverity
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
            tasks.append(process_single_file(file, output_dir, config))
            
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

async def process_single_file(
    input_file: Path,
    output_dir: Path,
    config: NovaConfig
) -> None:
    """Process a single markdown file."""
    try:
        logger.debug("processing_file", file=str(input_file))
        
        # Read input file
        async with aiofiles.open(input_file, 'r', encoding='utf-8') as f:
            content = await f.read()
            
        # Initialize markdown parser
        md = MarkdownIt('commonmark', {
            'typographer': config.markdown.typographer,
            'linkify': config.markdown.linkify,
            'breaks': config.markdown.breaks
        })
        
        # Add plugins
        for plugin in config.markdown.plugins:
            if hasattr(md, f'enable_{plugin}'):
                getattr(md, f'enable_{plugin}')()
                
        # Parse and validate content
        html = md.render(content)
        
        # Write processed file
        output_file = output_dir / input_file.name
        async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
            await f.write(html)
            
        logger.debug("file_processed",
                    input_file=str(input_file),
                    output_file=str(output_file))
                    
    except Exception as e:
        logger.error("file_processing_error",
                    file=str(input_file),
                    error=str(e))
        raise ProcessingError(f"Failed to process {input_file.name}: {str(e)}",
                            severity=ErrorSeverity.ERROR,
                            source=str(input_file)) 