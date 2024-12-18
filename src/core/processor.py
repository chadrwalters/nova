import os
import re
from pathlib import Path
import json
from typing import Optional
from datetime import datetime, UTC
from .logging import get_logger
from .errors import ErrorHandler, ProcessingError, ErrorSeverity
from .config import NovaConfig
import aiofiles
from markitdown import MarkItDown
import urllib.parse
import shutil
import base64
from PIL import Image
import pillow_heif  # For HEIC support

logger = get_logger(__name__)

def extract_metadata_from_filename(filename: str) -> dict:
    """Extract metadata from filename in format YYYYMMDD - Title.md"""
    pattern = r'^(\d{4})(\d{2})(\d{2})\s*-\s*(.+)\.md$'
    match = re.match(pattern, filename)
    
    if match:
        year, month, day, title = match.groups()
        return {
            "date": f"{year}-{month}-{day}",
            "title": title.strip()
        }
    return {"date": "", "title": ""}

async def process_markdown_file(input_file: Path, output_dir: Path, config: NovaConfig) -> bool:
    """Process a single markdown file."""
    try:
        logger.debug("processing_file", file=str(input_file))
        
        # Read input file
        async with aiofiles.open(input_file, 'r', encoding='utf-8') as f:
            content = await f.read()
            
        # Extract and save base64 images before other processing
        content = await extract_base64_images(
            content=content,
            output_dir=output_dir / input_file.stem / "images"
        )
            
        # Extract metadata from filename
        metadata = extract_metadata_from_filename(input_file.name)
        metadata["filename"] = input_file.name
        metadata["processed_timestamp"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Write processed file first to get output_file path
        output_file = output_dir / input_file.name
        async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
            await f.write(content)
            
        # Write metadata
        meta_file = output_file.with_suffix('.md.meta.json')
        async with aiofiles.open(meta_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(metadata, indent=4) + '\n')
            
        # First copy any embedded document attachments
        content = await copy_attachments(
            content=content,
            input_dir=input_file.parent,
            output_dir=output_dir / input_file.stem
        )
            
        # Process embedded documents
        content = await process_embedded_documents(
            content,
            output_dir / input_file.stem  # Use the copied attachments path
        )
            
        return True
        
    except Exception as e:
        logger.error("file_processing_failed",
                    file=str(input_file),
                    error=str(e))
        return False

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
            "processed_timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
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
                'timestamp': datetime.now(UTC).isoformat() + "Z",
                'changes': list(set(source_data.keys()) - set(dest_data.keys()))
            })
        else:
            merged = source_data
            merged['_processing_history'] = [{
                'phase': 'markdown_parse',
                'timestamp': datetime.now(UTC).isoformat() + "Z",
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

async def process_embedded_documents(content: str, base_path: Path) -> str:
    """Process embedded document references and replace with content."""
    pattern = r'\[([^\]]+)\]\(([^)]+)\)<!-- *(\{.*?\}) *-->'
    
    def validate_path(path: str) -> bool:
        """Validate path is safe and within allowed directories."""
        try:
            # Check for path traversal attempts
            if '..' in path or path.startswith('/'):
                logger.error("invalid_path_detected", path=path)
                return False
            return True
        except Exception as e:
            logger.error("path_validation_failed", path=path, error=str(e))
            return False
    
    async def process_document(match) -> str:
        title = match.group(1)
        path = match.group(2)
        options = json.loads(match.group(3))
        
        if not options.get('embed'):
            return match.group(0)
            
        if not validate_path(path):
            return f"""
> **Error**: Invalid path detected
> - Title: {title}
> - Path: {path}
"""
        
        # Use same path structure as copy_attachments
        doc_path = base_path / path.replace('%20', ' ')
        
        logger.debug("processing_document",
                    title=title,
                    path=str(doc_path),
                    options=options)
        
        if not doc_path.exists():
            logger.error("document_not_found", path=str(doc_path))
            return f"""
> **Warning**: Embedded document not found
> - File: {doc_path.name}
> - Path: {path}
> Please ensure document exists in input directory
"""
        
        try:
            # Use Microsoft's MarkItDown for all document types
            markitdown = MarkItDown()
            result = markitdown.convert(str(doc_path))
            content = result.text_content
            
            return f"""
## Embedded Document: {title}

<!-- Document Info:
Source: {doc_path.name}
Processed: {datetime.now(UTC).isoformat()}
-->

{content}
"""
            
        except Exception as e:
            logger.error("document_processing_failed",
                        file=str(doc_path),
                        error=str(e))
            return f"""
> **Error**: Failed to process document
> - File: {doc_path.name}
> - Error: {str(e)}
> Processing failed
"""
    
    # Process all matches
    for match in re.finditer(pattern, content):
        replacement = await process_document(match)
        content = content.replace(match.group(0), replacement)
        
    return content

async def copy_attachments(content: str, input_dir: Path, output_dir: Path) -> str:
    """Copy embedded document attachments and images to processing directory."""
    patterns = {
        'document': r'\[([^\]]+)\]\(([^)]+)\)<!-- *(\{.*?\}) *-->',
        'image': r'!\[([^\]]*)\]\(([^)]+)\)'
    }
    
    def validate_path(path: str) -> bool:
        """Validate path is safe and within allowed directories."""
        try:
            # Check for path traversal attempts
            if '..' in path or path.startswith('/'):
                logger.error("invalid_path_detected", path=path)
                return False
            # Skip data URLs
            if path.startswith('data:'):
                return False
            return True
        except Exception as e:
            logger.error("path_validation_failed", path=path, error=str(e))
            return False
    
    def get_mime_type(file_path: Path) -> str:
        """Get MIME type of file."""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or 'application/octet-stream'
    
    def convert_heic_to_jpeg(src_path: Path, dest_dir: Path) -> Optional[Path]:
        """Convert HEIC image to JPEG format."""
        try:
            # Register HEIF opener with Pillow
            pillow_heif.register_heif_opener()
            
            # Read HEIC image
            image = Image.open(src_path)
            
            # Create JPEG filename
            jpeg_name = src_path.stem + '.jpg'
            jpeg_path = dest_dir / jpeg_name
            
            # Convert and save as JPEG
            if image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])
                background.save(jpeg_path, 'JPEG', quality=95)
            else:
                image.convert('RGB').save(jpeg_path, 'JPEG', quality=95)
                
            logger.info("heic_converted",
                       src=str(src_path),
                       dest=str(jpeg_path))
            
            return jpeg_path
        except Exception as e:
            logger.error("heic_conversion_failed",
                        src=str(src_path),
                        error=str(e))
            return None
    
    async def process_image(match) -> str:
        """Process and copy image files."""
        alt_text = match.group(1)
        path = match.group(2)
        
        if not validate_path(path):
            return match.group(0)
        
        # Get source and destination paths
        src_path = input_dir / path.replace('%20', ' ')
        image_dir = output_dir / "images"
        dest_path = image_dir / Path(path.replace('%20', ' ')).name
        
        # Copy image if it exists
        if src_path.exists():
            mime_type = get_mime_type(src_path)
            # Handle HEIC images
            if src_path.suffix.lower() in ('.heic', '.heif'):
                image_dir.mkdir(parents=True, exist_ok=True)
                jpeg_path = convert_heic_to_jpeg(src_path, image_dir)
                if jpeg_path:
                    return f"![{alt_text}](images/{jpeg_path.name})"
                return match.group(0)
            
            if not mime_type.startswith('image/'):
                logger.warning("not_an_image",
                             src=str(src_path),
                             mime_type=mime_type)
                return match.group(0)
            
            image_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dest_path)
            logger.info("image_copied",
                       src=str(src_path),
                       dest=str(dest_path),
                       mime_type=mime_type)
            return f"![{alt_text}](images/{dest_path.name})"
        else:
            logger.warning("image_not_found",
                         src=str(src_path),
                         alt=alt_text)
            return match.group(0)
    
    async def process_attachment(match) -> str:
        title = match.group(1)
        path = match.group(2)
        options = json.loads(match.group(3))
        
        if not validate_path(path):
            return match.group(0)
        
        # Get source and destination paths
        src_path = input_dir / path.replace('%20', ' ')
        dest_dir = output_dir
        dest_path = dest_dir / Path(path.replace('%20', ' ')).name
        
        # Copy file if it exists
        if src_path.exists():
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dest_path)
            logger.info("attachment_copied",
                       src=str(src_path),
                       dest=str(dest_path))
        else:
            logger.warning("attachment_not_found",
                         src=str(src_path),
                         title=title)
        
        return match.group(0)
    
    # Process all patterns
    for pattern_type, pattern in patterns.items():
        for match in re.finditer(pattern, content):
            if pattern_type == 'document':
                await process_attachment(match)
            else:  # image
                replacement = await process_image(match)
                content = content.replace(match.group(0), replacement)
    
    return content

async def extract_base64_images(content: str, output_dir: Path) -> str:
    """Extract base64 encoded images and save them to files."""
    base64_pattern = r'!\[([^\]]*)\]\(data:image/([^;]+);base64,([^\)]+)\)'
    
    async def save_base64_image(match) -> str:
        alt_text = match.group(1)
        img_type = match.group(2)
        base64_data = match.group(3)
        
        try:
            # Decode base64 data
            image_data = base64.b64decode(base64_data)
            
            # Use markitdown to validate and process image
            markitdown = MarkItDown()
            try:
                result = markitdown.validate_image(image_data)
                if not result.is_valid:
                    logger.warning("invalid_base64_image", alt=alt_text)
                    return match.group(0)
                detected_type = result.image_type
            except Exception:
                logger.warning("invalid_base64_image", alt=alt_text)
                return match.group(0)
            
            # Generate filename from alt text or use default
            safe_alt = re.sub(r'[^\w\-_.]', '_', alt_text or 'image')
            filename = f"{safe_alt}_{hash(str(image_data))[:8]}.{detected_type}"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save image file
            image_path = output_dir / filename
            async with aiofiles.open(image_path, 'wb') as f:
                await f.write(image_data)
            
            logger.info("base64_image_saved", 
                       alt=alt_text,
                       path=str(image_path))
            
            # Return markdown link to saved image
            return f"![{alt_text}](images/{filename})"
            
        except Exception as e:
            logger.error("base64_image_failed",
                        alt=alt_text,
                        error=str(e))
            return match.group(0)
    
    # Process all base64 images
    for match in re.finditer(base64_pattern, content):
        replacement = await save_base64_image(match)
        content = content.replace(match.group(0), replacement)
    
    return content
