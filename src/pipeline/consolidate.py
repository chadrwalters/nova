from pathlib import Path
import asyncio
import aiofiles
from typing import List, Dict, Any
from ..core.config import NovaConfig
from ..core.logging import get_logger
from ..core.errors import ProcessingError, ErrorSeverity
import json
import re

logger = get_logger(__name__)

async def consolidate_markdown(config: NovaConfig) -> bool:
    """Consolidate processed markdown files."""
    try:
        input_dir = config.processing.phase_markdown_parse
        output_dir = config.processing.phase_markdown_consolidate
        
        # Ensure directories exist
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get list of markdown files
        markdown_files = sorted(list(input_dir.glob("*.md")))
        if not markdown_files:
            logger.warning("no_markdown_files_found", input_dir=str(input_dir))
            return False
            
        logger.info("consolidating_markdown_files",
                   file_count=len(markdown_files),
                   input_dir=str(input_dir))
        
        # Read all files and their metadata
        files_data = []
        for file in markdown_files:
            try:
                content, metadata = await read_file_with_metadata(file)
                files_data.append({
                    'file': file,
                    'content': content,
                    'metadata': metadata
                })
            except Exception as e:
                logger.error("file_read_failed",
                           file=str(file),
                           error=str(e))
                return False
                
        # Sort files by date if available
        files_data.sort(key=lambda x: x['metadata'].get('date', x['file'].name))
        
        # Consolidate content
        consolidated_content = []
        for data in files_data:
            try:
                # Add file header
                consolidated_content.append(f"\n## {data['metadata'].get('title', data['file'].name)}\n")
                
                # Add metadata as HTML comment
                meta_comment = f"<!--\nSource: {data['file'].name}\n"
                for key, value in data['metadata'].items():
                    meta_comment += f"{key}: {value}\n"
                meta_comment += "-->\n"
                consolidated_content.append(meta_comment)
                
                # Add content
                consolidated_content.append(data['content'])
                consolidated_content.append("\n---\n")  # Section separator
                
            except Exception as e:
                logger.error("consolidation_failed",
                           file=str(data['file']),
                           error=str(e))
                return False
                
        # Write consolidated file
        try:
            output_file = output_dir / "consolidated.md"
            async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
                await f.write("\n".join(consolidated_content))
                
            logger.info("consolidation_complete",
                       output_file=str(output_file))
            return True
            
        except Exception as e:
            logger.error("write_failed",
                        file=str(output_file),
                        error=str(e))
            return False
            
    except Exception as e:
        logger.error("consolidation_failed", error=str(e))
        return False

async def read_file_with_metadata(file_path: Path) -> tuple[str, Dict[str, Any]]:
    """Read a markdown file and its metadata."""
    try:
        # Read markdown file
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            
        # Try to read metadata file
        metadata = {}
        meta_file = file_path.with_suffix('.md.meta.json')
        if meta_file.exists():
            try:
                async with aiofiles.open(meta_file, 'r', encoding='utf-8') as f:
                    metadata = json.loads(await f.read())
            except Exception as e:
                logger.warning("metadata_read_failed",
                             file=str(meta_file),
                             error=str(e))
                
        # Extract title from content if not in metadata
        if 'title' not in metadata:
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            if title_match:
                metadata['title'] = title_match.group(1).strip()
            else:
                metadata['title'] = file_path.stem
                
        return content, metadata
        
    except Exception as e:
        logger.error("file_read_failed",
                    file=str(file_path),
                    error=str(e))
        raise ProcessingError(f"Failed to read {file_path.name}: {str(e)}",
                            severity=ErrorSeverity.ERROR,
                            source=str(file_path)) 