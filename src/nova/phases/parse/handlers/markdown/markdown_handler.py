"""Handler for processing markdown files."""

from pathlib import Path
from typing import Dict, Any, List, Optional
import aiofiles
import yaml
import re
from datetime import date, datetime
from urllib.parse import unquote, quote
import json
import shutil
import logging
import mimetypes
import base64
import os
import uuid
import tempfile
import markitdown

from nova.phases.core.base_handler import BaseHandler, HandlerResult
from nova.core.logging import get_logger
from .document_converter import DocumentConverter, ConversionResult
from .image_converter import ImageConverter, ImageConversionResult

logger = get_logger(__name__)

class MarkdownHandler(BaseHandler):
    """Handles markdown file processing."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the markdown handler."""
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Configure processing options
        self.document_conversion = self.get_option('document_conversion', True)
        self.image_processing = self.get_option('image_processing', True)
        self.metadata_preservation = self.get_option('metadata_preservation', True)
        
        # Initialize converters
        self.document_converter = DocumentConverter()
        self.image_converter = ImageConverter()
        
        # Initialize input directory
        self.input_dir = None
    
    def can_handle(self, file_path: Path, attachments: Optional[List[Path]] = None) -> bool:
        """Check if file can be processed."""
        return file_path.suffix.lower() in {'.md', '.markdown'}
    
    async def _process_initial_links(self, content: str, output_dir: Path, file_stem: str) -> str:
        """Process initial links in the content."""
        try:
            # Find all links with embed metadata and image links
            patterns = [
                (r'\* ([^:]+)(?::\s*)?\[([^\]]+)\]\(([^)]+)\)(?:<!-- \{"embed":"true"\} -->)?', False),  # Links with label
                (r'\* ([^:]+)(?::\s*)?!\[([^\]]*)\]\(([^)]+)\)', True),  # Image links with label
                (r'\[([^\]]+)\]\(([^)]+)\)(?:<!-- \{"embed":"true"\} -->)?', False),  # Links with optional embed metadata
                (r'!\[\]\(([^)]+)\)', True),  # Image links without alt text
                (r'!\[([^\]]*)\]\(([^)]+)\)', True)  # Image links with alt text
            ]
            
            for pattern, is_image_pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    try:
                        if len(match.groups()) == 3:  # Pattern with label
                            label = match.group(1)
                            link_text = match.group(2)
                            path = unquote(match.group(3))
                        elif '<!-- {"embed":"true"} -->' in pattern:
                            label = None
                            link_text = match.group(1)
                            path = unquote(match.group(2))
                        elif '!\[\]' in pattern:
                            label = None
                            link_text = ''
                            path = unquote(match.group(1))
                        else:
                            label = None
                            link_text = match.group(1)
                            path = unquote(match.group(2))

                        file_name = os.path.basename(path)
                        
                        # Get the full path
                        full_path = os.path.join(self.input_dir, path)
                        if not os.path.exists(full_path):
                            continue
                        
                        # Create markdown's directory for attachments
                        markdown_dir = output_dir / file_stem
                        markdown_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Determine file type
                        mime_type, _ = mimetypes.guess_type(str(full_path))
                        is_image = mime_type and mime_type.startswith('image/')
                        ext = Path(file_name).suffix.lower()
                        
                        if is_image:
                            if ext in {'.heic', '.heif'} and self.image_processing:
                                # Convert HEIC/HEIF to JPG
                                result: ImageConversionResult = await self.image_converter.convert_image(Path(full_path))
                                if result.success:
                                    # Save converted image
                                    new_name = f"{Path(file_name).stem}.{result.format}"
                                    target_file = markdown_dir / new_name
                                    async with aiofiles.open(target_file, 'wb') as f:
                                        await f.write(result.content)
                                    self.logger.info(f"Converted {file_name} to {new_name}")
                                    file_name = new_name
                                    
                                    # Add dimensions to link text if not provided
                                    if not link_text:
                                        link_text = f"{Path(file_name).stem} ({result.dimensions[0]}x{result.dimensions[1]})"
                                else:
                                    # Fallback to copying original if conversion fails
                                    target_file = markdown_dir / file_name
                                    if not target_file.exists():
                                        shutil.copy2(full_path, target_file)
                                    self.logger.warning(f"Failed to convert {file_name}: {result.error}")
                            else:
                                # Copy non-HEIC image as is
                                target_file = markdown_dir / file_name
                                if not target_file.exists():
                                    shutil.copy2(full_path, target_file)
                                    self.logger.info(f"Copied {file_name} to {target_file}")
                            
                            # Remove any existing files with same stem but different extensions
                            for existing in markdown_dir.glob(f"{Path(file_name).stem}.*"):
                                if existing != target_file:
                                    try:
                                        existing.unlink()
                                        self.logger.info(f"Removed duplicate file: {existing}")
                                    except Exception as e:
                                        self.logger.warning(f"Failed to remove duplicate file {existing}: {str(e)}")
                        else:
                            # Copy non-image file to markdown's directory
                            target_file = markdown_dir / file_name
                            if not target_file.exists():
                                shutil.copy2(full_path, target_file)
                                self.logger.info(f"Copied {file_name} to {target_file}")
                        
                        # Update link in content to point to attachment in markdown's directory
                        rel_path = f"{file_stem}/{file_name}"
                        
                        # Update link in content based on pattern type
                        if is_image_pattern:
                            # For image patterns
                            if not link_text:
                                # For image links without alt text, use the filename as alt text
                                link_text = os.path.splitext(file_name)[0]
                            new_link = f'![{link_text}]({rel_path})'
                            if label:
                                new_link = f'* {label}: {new_link}'
                            content = content.replace(match.group(0), new_link)
                        else:
                            # For regular links
                            if not link_text:
                                # For links without text, use the filename as link text
                                link_text = os.path.splitext(file_name)[0]
                            new_link = f'[{link_text}]({rel_path})<!-- {{"embed":"true"}} -->'
                            if label:
                                new_link = f'* {label}: {new_link}'
                            content = content.replace(match.group(0), new_link)
                            
                    except Exception as e:
                        self.logger.error(f"Failed to process initial link {match.group(0)}: {str(e)}")
                        continue
            
            return content
            
        except Exception as e:
            self.logger.error(f"Failed to process initial links: {str(e)}")
            return content
    
    async def process(
        self,
        file_path: Path,
        context: Dict[str, Any],
        attachments: Optional[List[Path]] = None
    ) -> HandlerResult:
        """Process markdown file and its attachments."""
        result = HandlerResult()
        result.start_time = datetime.now()
        
        try:
            # Set input directory
            self.input_dir = file_path.parent
            
            # Read markdown file
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            if content is None:
                content = ""
            
            # Create output directory
            output_dir = Path(context['output_dir'])
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Process initial links
            content = await self._process_initial_links(content, output_dir, context['file_stem'])
            if content is None:
                content = ""
            
            # Process base64 encoded images if enabled
            if self.image_processing:
                content = await self._process_base64_images(content, output_dir, context['file_stem'])
                if content is None:
                    content = ""
            
            # Process attachments if present
            if attachments:
                self.logger.info(f"Processing {len(attachments)} attachments")
                for attachment in attachments:
                    content = await self._process_attachment(content, attachment, output_dir, context['file_stem'])
                    if content is None:
                        content = ""
            
            # Write processed content
            output_file = output_dir / file_path.name
            async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            # Update result
            result.content = content
            result.processed_files.append(file_path)
            if attachments:
                result.processed_attachments.extend(attachments)
            
        except Exception as e:
            result.add_error(f"Failed to process {file_path}: {str(e)}")
            self.logger.error(f"Error processing {file_path}: {str(e)}", exc_info=True)
        
        finally:
            result.end_time = datetime.now()
            if result.start_time:
                result.processing_time = (result.end_time - result.start_time).total_seconds()
        
        return result
    
    async def _process_base64_images(self, content: str, output_dir: Path, file_stem: str) -> str:
        """Extract base64 encoded images and save them as files."""
        try:
            # Create markdown's directory for attachments
            markdown_dir = output_dir / file_stem
            markdown_dir.mkdir(parents=True, exist_ok=True)
            
            # Find base64 encoded images
            pattern = r'!\[([^\]]*)\]\(data:image/([^;]+);base64,([^\)]+)\)'
            matches = re.finditer(pattern, content)
            
            for match in matches:
                try:
                    alt_text = match.group(1)
                    image_type = match.group(2)
                    base64_data = match.group(3)
                    
                    # Generate filename
                    filename = f"image_{uuid.uuid4().hex[:8]}.{image_type}"
                    
                    # Save image file in markdown's directory
                    image_path = markdown_dir / filename
                    image_data = base64.b64decode(base64_data)
                    async with aiofiles.open(image_path, 'wb') as f:
                        await f.write(image_data)
                    
                    # Update content with new image reference
                    rel_path = f"{file_stem}/{filename}"
                    new_link = f'![{alt_text}]({rel_path})'
                    content = content.replace(match.group(0), new_link)
                    
                except Exception as e:
                    self.logger.error(f"Failed to process base64 image: {str(e)}")
                    continue
            
            return content
            
        except Exception as e:
            self.logger.error(f"Failed to process base64 images: {str(e)}")
            return content
    
    async def _process_attachment(self, content: str, attachment: Path, output_dir: Path, file_stem: str) -> str:
        """Process an attachment and create markdown content for it."""
        if content is None:
            content = ""
            
        try:
            # Create markdown's directory for attachments
            markdown_dir = output_dir / file_stem
            markdown_dir.mkdir(parents=True, exist_ok=True)
            
            # Determine file type
            mime_type, _ = mimetypes.guess_type(str(attachment))
            is_image = mime_type and mime_type.startswith('image/')
            ext = attachment.suffix.lower()
            
            # Initialize target_file and markdown content
            target_file = markdown_dir / attachment.name
            markdown = ""
            
            if is_image:
                # Handle image attachment
                if ext in {'.heic', '.heif'} and self.image_processing:
                    # Convert HEIC/HEIF to JPG
                    result: ImageConversionResult = await self.image_converter.convert_image(attachment)
                    if result.success:
                        # Save converted image
                        new_name = f"{attachment.stem}.{result.format}"
                        target_file = markdown_dir / new_name
                        async with aiofiles.open(target_file, 'wb') as f:
                            await f.write(result.content)
                        self.logger.info(f"Converted {attachment.name} to {new_name}")
                        
                        # Create markdown with metadata
                        rel_path = f"{file_stem}/{new_name}"
                        markdown = f'\n![{attachment.stem} ({result.dimensions[0]}x{result.dimensions[1]})]({rel_path})\n'
                        if self.metadata_preservation:
                            markdown += f'<!-- {json.dumps(result.metadata)} -->\n'
                    else:
                        # Fallback to copying original if conversion fails
                        target_file = markdown_dir / attachment.name
                        if not target_file.exists():
                            shutil.copy2(attachment, target_file)
                        rel_path = f"{file_stem}/{attachment.name}"
                        markdown = f'\n![{attachment.stem}]({rel_path})\n'
                        if self.metadata_preservation:
                            stats = attachment.stat()
                            metadata = {
                                'type': mime_type or 'application/octet-stream',
                                'size': stats.st_size,
                                'modified': datetime.fromtimestamp(stats.st_mtime).isoformat()
                            }
                            markdown += f'<!-- {json.dumps(metadata)} -->\n'
                else:
                    # Copy non-HEIC image as is
                    target_file = markdown_dir / attachment.name
                    if not target_file.exists():
                        shutil.copy2(attachment, target_file)
                    rel_path = f"{file_stem}/{attachment.name}"
                    markdown = f'\n![{attachment.stem}]({rel_path})\n'
                    if self.metadata_preservation:
                        stats = attachment.stat()
                        metadata = {
                            'type': mime_type or 'application/octet-stream',
                            'size': stats.st_size,
                            'modified': datetime.fromtimestamp(stats.st_mtime).isoformat()
                        }
                        markdown += f'<!-- {json.dumps(metadata)} -->\n'

                # Remove any existing files with same stem but different extensions
                for existing in markdown_dir.glob(f"{attachment.stem}.*"):
                    if existing != target_file:
                        try:
                            existing.unlink()
                            self.logger.info(f"Removed duplicate file: {existing}")
                        except Exception as e:
                            self.logger.warning(f"Failed to remove duplicate file {existing}: {str(e)}")

            else:
                # Handle document attachment
                # Copy file to markdown directory first
                target_file = markdown_dir / attachment.name
                if not target_file.exists():
                    shutil.copy2(attachment, target_file)
                
                if self.document_conversion:
                    # Convert document to markdown
                    result = await self.document_converter.convert_to_markdown(attachment)
                    if result.success:
                        # Create markdown with converted content and metadata
                        markdown = f'\n## {attachment.stem}\n\n{result.content}\n'
                        if self.metadata_preservation:
                            metadata = {
                                'type': mime_type or 'application/octet-stream',
                                'original_file': attachment.name,
                                'converter': result.converter_name
                            }
                            markdown += f'<!-- {json.dumps(metadata)} -->\n'
                            
                        # Also save as separate markdown file
                        md_filename = f"{attachment.stem}.md"
                        md_file = markdown_dir / md_filename
                        async with aiofiles.open(md_file, 'w', encoding='utf-8') as f:
                            await f.write(f"# {attachment.stem}\n\n{result.content}\n")
                            if self.metadata_preservation:
                                await f.write(f'<!-- {json.dumps(metadata)} -->\n')
                        self.logger.info(f"Created markdown file: {md_file}")
                    else:
                        # If conversion fails, add link to original file
                        rel_path = f"{file_stem}/{attachment.name}"
                        markdown = f'\n[{attachment.stem}]({rel_path})<!-- {{"embed":"true"}} -->\n'
                        if self.metadata_preservation:
                            stats = attachment.stat()
                            metadata = {
                                'type': mime_type or 'application/octet-stream',
                                'size': stats.st_size,
                                'modified': datetime.fromtimestamp(stats.st_mtime).isoformat(),
                                'conversion_error': result.error
                            }
                            markdown += f'<!-- {json.dumps(metadata)} -->\n'
                else:
                    # If document conversion is disabled, just add link to original file
                    rel_path = f"{file_stem}/{attachment.name}"
                    markdown = f'\n[{attachment.stem}]({rel_path})<!-- {{"embed":"true"}} -->\n'
                    if self.metadata_preservation:
                        stats = attachment.stat()
                        metadata = {
                            'type': mime_type or 'application/octet-stream',
                            'size': stats.st_size,
                            'modified': datetime.fromtimestamp(stats.st_mtime).isoformat()
                        }
                        markdown += f'<!-- {json.dumps(metadata)} -->\n'

            # Add markdown to content and return
            return content + markdown

        except Exception as e:
            self.logger.error(f"Failed to process attachment {attachment}: {str(e)}")
            return content
    
    def validate_output(self, result: HandlerResult) -> bool:
        """Validate the processing results."""
        if not isinstance(result, HandlerResult):
            return False
            
        # Check required attributes
        if not hasattr(result, 'content') or not result.content:
            return False
            
        if not hasattr(result, 'processed_files') or not result.processed_files:
            return False
            
        # Attachments are optional
        if hasattr(result, 'processed_attachments') and result.processed_attachments:
            if not all(isinstance(p, Path) for p in result.processed_attachments):
                return False
                
        return True 