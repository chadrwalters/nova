import os
import re
from pathlib import Path
import json
from datetime import datetime
import threading
from .logging import get_logger
from .validation import validate_markdown_content, process_embedded_docs
from .context import document_context, get_current_frontmatter
from .errors import ErrorHandler, ProcessingError, ErrorSeverity
from .docx_processor import WordProcessor
from .config import NovaConfig
import aiofiles

logger = get_logger(__name__)

async def process_word_attachments(content: str, config: NovaConfig, error_handler: ErrorHandler) -> str:
    """Process any Word document attachments referenced in the markdown."""
    try:
        processor = WordProcessor(config, error_handler)
        
        # Find Word document references
        pattern = r'\[([^\]]+)\]\(([^)]+\.docx?)\)'
        matches = re.finditer(pattern, content)
        
        # Process each reference
        for match in matches:
            title = match.group(1)
            doc_path = match.group(2)
            
            # Convert relative path to absolute
            if not os.path.isabs(doc_path):
                doc_path = os.path.join(config.processing.input_dir, doc_path)
            
            # Process the document
            markdown = await processor.process_document(Path(doc_path), title, {})
            
            # Replace the reference with the markdown content
            content = content.replace(match.group(0), markdown)
            
        return content
        
    except Exception as e:
        error_handler.add_error(ProcessingError(
            message=str(e),
            severity=ErrorSeverity.ERROR,
            source="process_word_attachments",
            details={"error": str(e)}
        ))
        return content

async def process_markdown_file(input_file, output_dir, config):
    """
    Process a single markdown file through the first phase
    """
    error_handler = ErrorHandler(config.processing.error_tolerance)
    try:
        input_path = Path(input_file)
        with document_context():
            async with aiofiles.open(input_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                
            # Process embedded documents before validation
            content = await process_embedded_docs(content, config, input_path)
            
            # Process horizontal rules before validation
            content = process_horizontal_rules(content)
            
            # Validate and clean content
            processed_content = await validate_markdown_content(
                content, config, source_file=input_path, error_handler=error_handler
            )
            
            # Handle metadata
            meta_file = input_path.with_suffix('.md.meta.json')
            output_meta = Path(output_dir) / meta_file.name
            
            # Update and copy metadata
            await update_metadata(input_path, processed_content, meta_file)
            await copy_and_merge_metadata(meta_file, output_meta)
            
            # Create output filename
            output_file = Path(output_dir) / input_path.name
            
            # Write processed content
            async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
                await f.write(processed_content)
                
        # Check for critical errors
        if error_handler.has_errors(ErrorSeverity.CRITICAL):
            logger.error("critical_error", file=str(input_file))
            return False
            
        logger.info("markdown_processed", file=str(input_file))
        return True
        
    except Exception as e:
        logger.error("file_processing_failed",
                    file_path=str(input_file),
                    error=str(e))
        raise

def process_horizontal_rules(content):
    """
    Standardize horizontal rules in markdown
    """
    # Add newlines before replacement to ensure proper spacing
    content = '\n' + content + '\n'
    
    # Replace various HR formats with standard format
    hr_patterns = [
        r'^\s*[-]{3,}\s*$',  # Three or more hyphens
        r'^\s*[_]{3,}\s*$',  # Three or more underscores
        r'^\s*[\*]{3,}\s*$'  # Three or more asterisks
    ]
    
    for pattern in hr_patterns:
        content = re.sub(pattern, '\n---\n', content, flags=re.MULTILINE)
    
    # Clean up multiple newlines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return content.strip() 

async def update_metadata(input_path: Path, content: str, meta_file: Path) -> None:
    """Update metadata for a markdown file."""
    try:
        # Get current frontmatter from thread-local storage
        frontmatter = get_current_frontmatter()
        
        # Create base metadata
        metadata = {
            "filename": input_path.name,
            "date": frontmatter.get("date", ""),
            "title": frontmatter.get("title", ""),
            "toc": [],  # Initialize empty to avoid trailing comma issues
            "processed_timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        
        # Extract table of contents
        headers = re.findall(r'^(#{1,6})\s+(.+)$', content, re.MULTILINE)
        if headers:
            metadata["toc"] = [h[1].strip() for h in headers]
        
        # Write metadata with proper JSON formatting
        async with aiofiles.open(meta_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(metadata, indent=4, ensure_ascii=False) + '\n')
            
    except Exception as e:
        logger.error("metadata_update_failed", error=str(e), file=str(input_path))
        # Don't fail processing if metadata update fails

async def copy_and_merge_metadata(source_meta: Path, dest_meta: Path) -> None:
    """Copy metadata file to output directory, merging with existing if present."""
    try:
        # Read source metadata
        if source_meta.exists():
            async with aiofiles.open(source_meta, 'r') as f:
                source_data = json.loads(await f.read())
        else:
            source_data = {}
            
        # Read destination metadata if it exists
        if dest_meta.exists():
            async with aiofiles.open(dest_meta, 'r') as f:
                dest_data = json.loads(await f.read())
                
            # Merge metadata, preserving phase-specific information
            merged = dest_data.copy()
            merged.update(source_data)  # Source data takes precedence
            
            # Preserve processing history
            if '_processing_history' not in merged:
                merged['_processing_history'] = []
            merged['_processing_history'].append({
                'phase': 'markdown_parse',
                'timestamp': datetime.utcnow().isoformat() + "Z",
                'changes': list(set(source_data.keys()) - set(dest_data.keys()))
            })
        else:
            merged = source_data
            merged['_processing_history'] = [{
                'phase': 'markdown_parse',
                'timestamp': datetime.utcnow().isoformat() + "Z",
                'changes': list(source_data.keys())
            }]
            
        # Write merged metadata
        async with aiofiles.open(dest_meta, 'w') as f:
            await f.write(json.dumps(merged, indent=4) + '\n')
            
    except Exception as e:
        logger.error("metadata_copy_failed", 
                     source=str(source_meta), 
                     destination=str(dest_meta), 
                     error=str(e))
        raise
