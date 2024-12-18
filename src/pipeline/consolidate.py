from pathlib import Path
import asyncio
import aiofiles
from typing import List, Dict, Any
from ..core.config import NovaConfig
from ..core.logging import get_logger
from ..core.errors import ProcessingError, ErrorSeverity
from ..processors.pdf_generator import generate_pdf
import json
import re
from ..core.processor import process_embedded_documents

logger = get_logger(__name__)

async def consolidate_markdown(config: NovaConfig) -> bool:
    """Consolidate markdown files into a single document."""
    try:
        input_dir = config.processing.phase_markdown_parse
        output_dir = config.processing.phase_markdown_consolidate
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get all markdown files and sort by date
        markdown_files = sorted(input_dir.glob("*.md"))
        consolidated_content = []
        consolidated_meta = {}
        
        for file in markdown_files:
            try:
                # Read markdown content
                async with aiofiles.open(file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                
                # Process embedded documents
                content = await process_embedded_documents(
                    content,
                    file.parent
                )
                
                # Read metadata
                meta_file = file.with_suffix('.md.meta.json')
                if meta_file.exists():
                    async with aiofiles.open(meta_file, 'r', encoding='utf-8') as f:
                        metadata = json.loads(await f.read())
                else:
                    metadata = {}
                
                # Create metadata comment
                meta_comment = "<!--\n"
                meta_comment += f"Source: {file.name}\n"
                for key, value in metadata.items():
                    if key != '_processing_history':
                        meta_comment += f"{key}: {value}\n"
                meta_comment += "-->"
                
                # Extract original H1 if present
                h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                original_title = h1_match.group(1) if h1_match else None
                
                # Remove any existing frontmatter
                content = re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, flags=re.DOTALL)
                
                # Only add our title if no original H1 exists
                title = metadata.get('title', file.stem)
                if not original_title:
                    consolidated_content.extend([
                        f"\n# {title}",
                        meta_comment,
                        content.strip() if content.strip() else f"[No content for {title}]",
                        "\n---\n"
                    ])
                else:
                    consolidated_content.extend([
                        meta_comment,
                        content.strip(),
                        "\n---\n"
                    ])
                
                # Store metadata with sequence info
                consolidated_meta[file.name] = {
                    **metadata,
                    "sequence": len(consolidated_meta) + 1
                }
                
            except Exception as e:
                logger.error("consolidation_failed",
                           file=str(file),
                           error=str(e))
                return False
        
        # Write consolidated content
        output_file = output_dir / "consolidated.md"
        async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
            await f.write('\n'.join(consolidated_content))
        
        # Write consolidated metadata
        meta_file = output_file.with_suffix('.md.meta.json')
        async with aiofiles.open(meta_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(consolidated_meta, indent=2))
        
        return True
        
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

async def process_pipeline(config: NovaConfig) -> bool:
    """Run the full document processing pipeline."""
    try:
        # First phase: Parse markdown
        if not await process_markdown_files(config):
            return False
            
        # Second phase: Consolidate markdown
        if not await consolidate_markdown(config):
            return False
            
        # Third phase: Generate PDF
        if not await generate_pdf(config):
            return False
            
        return True
        
    except Exception as e:
        logger.error("pipeline_failed", error=str(e))
        return False