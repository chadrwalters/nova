from pathlib import Path
import asyncio
import aiofiles
from typing import List, Dict, Any
from ..core.config import NovaConfig
from ..core.logging import get_logger
from ..core.errors import ProcessingError, ErrorSeverity
from ..processors.pdf_generator import PDFGenerator
import gc

logger = get_logger(__name__)

async def generate_pdfs(config: NovaConfig) -> bool:
    """Generate PDF files from consolidated markdown."""
    try:
        input_dir = config.processing.phase_markdown_consolidate
        output_dir = config.processing.phase_pdf_generate
        
        # Ensure directories exist
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get list of markdown files
        markdown_files = list(input_dir.glob("*.md"))
        if not markdown_files:
            logger.warning("no_markdown_files_found", input_dir=str(input_dir))
            return False
            
        logger.info("generating_pdfs",
                   file_count=len(markdown_files),
                   input_dir=str(input_dir))
        
        # Initialize PDF generator
        pdf_generator = PDFGenerator(config)
        
        # Process each file
        tasks = []
        for file in markdown_files:
            tasks.append(process_single_file(file, output_dir, pdf_generator))
            
        # Wait for all files to be processed
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for errors
        success = True
        for file, result in zip(markdown_files, results):
            if isinstance(result, Exception):
                logger.error("pdf_generation_failed",
                           file=str(file),
                           error=str(result))
                success = False
                
        return success
        
    except Exception as e:
        logger.error("pdf_generation_failed", error=str(e))
        return False
    finally:
        # Force garbage collection
        gc.collect()
        gc.collect()  # Second pass to clean up circular references

async def process_single_file(
    input_file: Path,
    output_dir: Path,
    pdf_generator: PDFGenerator
) -> None:
    """Process a single file to PDF."""
    try:
        logger.debug("processing_file", file=str(input_file))
        
        # Read input file
        async with aiofiles.open(input_file, 'r', encoding='utf-8') as f:
            content = await f.read()
            
        # Generate PDF filename
        pdf_file = output_dir / input_file.with_suffix('.pdf').name
        
        # Generate PDF
        await pdf_generator.generate_pdf(content, pdf_file)
        
        logger.debug("pdf_generated",
                    input_file=str(input_file),
                    output_file=str(pdf_file))
                    
    except Exception as e:
        logger.error("pdf_generation_error",
                    file=str(input_file),
                    error=str(e))
        raise ProcessingError(f"Failed to generate PDF for {input_file.name}: {str(e)}",
                            severity=ErrorSeverity.ERROR,
                            source=str(input_file)) 