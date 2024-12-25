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

from nova.phases.core.base_handler import BaseHandler, HandlerResult
from nova.core.logging import get_logger

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
                        
                        # Determine file type and target directory
                        mime_type, _ = mimetypes.guess_type(str(full_path))
                        ext = Path(file_name).suffix.lower()
                        
                        # Determine if the file is an image based on MIME type and extension
                        is_image = (mime_type and mime_type.startswith('image/')) or ext in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif'}
                        
                        # Set target directory based on file type
                        if is_image:
                            target_dir = 'images'
                        elif ext in {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'} or (mime_type and (mime_type.startswith('application/vnd.') or mime_type == 'application/pdf')):
                            target_dir = 'office'
                        else:
                            target_dir = 'documents'
                        
                        # Create target path
                        rel_path = f'{target_dir}/{file_stem}/{file_name}'
                        target_dir_path = output_dir / target_dir / file_stem
                        target_dir_path.mkdir(parents=True, exist_ok=True)
                        
                        # Copy file
                        target_file = target_dir_path / file_name
                        if not target_file.exists():
                            shutil.copy2(full_path, target_file)
                            self.logger.info(f"Copied {file_name} to {target_file}")
                        
                        # Update link in content based on file type and pattern type
                        if is_image_pattern and is_image:
                            # For image patterns pointing to image files
                            if not link_text:
                                # For image links without alt text, use the filename as alt text
                                link_text = os.path.splitext(file_name)[0]
                            new_link = f'![{link_text}]({rel_path})'
                            if label:
                                new_link = f'* {label}: {new_link}'
                            content = content.replace(match.group(0), new_link)
                        elif is_image_pattern and not is_image:
                            # For image patterns pointing to non-image files, convert to regular links
                            if not link_text:
                                # For links without text, use the filename as link text
                                link_text = os.path.splitext(file_name)[0]
                            new_link = f'[{link_text}]({rel_path})<!-- {{"embed":"true"}} -->'
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
            
            # Create output directory
            output_dir = Path(context['output_dir'])
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Process initial links
            content = await self._process_initial_links(content, output_dir, context['file_stem'])
            
            # Process base64 encoded images if enabled
            if self.image_processing:
                content = await self._process_base64_images(content, output_dir, context['file_stem'])
            
            # Process attachments if present
            if attachments:
                self.logger.info(f"Processing {len(attachments)} attachments")
                for attachment in attachments:
                    content = await self._process_attachment(content, attachment, output_dir, context['file_stem'])
            
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
            # Find all base64 encoded images
            pattern = r'!\[([^\]]*)\]\(data:image/([^;]+);base64,([^\)]+)\)'
            matches = re.finditer(pattern, content)
            
            for i, match in enumerate(matches):
                try:
                    alt_text = match.group(1)
                    image_type = match.group(2)
                    base64_data = match.group(3)
                    
                    # Create images directory
                    images_dir = output_dir / 'images' / file_stem
                    images_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Save image
                    image_name = f'embedded_image_{i}.{image_type}'
                    image_path = images_dir / image_name
                    
                    image_data = base64.b64decode(base64_data)
                    with open(image_path, 'wb') as f:
                        f.write(image_data)
                    
                    # Update markdown to reference the saved image
                    new_path = f'images/{file_stem}/{image_name}'
                    content = content.replace(match.group(0), f'![{alt_text}]({new_path})')
                    
                    self.logger.info(f"Extracted base64 image to {image_path}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to process base64 image: {str(e)}")
                    continue
            
            return content
            
        except Exception as e:
            self.logger.error(f"Failed to process base64 images: {str(e)}")
            return content
    
    async def _process_attachment(self, content: str, attachment: Path, output_dir: Path, file_stem: str) -> str:
        """Process an attachment and create markdown content for it."""
        try:
            # Initialize mimetypes with additional types
            mimetypes.init()
            mimetypes.add_type('application/pdf', '.pdf')
            mimetypes.add_type('application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx')
            mimetypes.add_type('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.xlsx')
            mimetypes.add_type('application/vnd.openxmlformats-officedocument.presentationml.presentation', '.pptx')
            
            mime_type, _ = mimetypes.guess_type(str(attachment))
            ext = attachment.suffix.lower()
            
            # Determine file type and target directory
            if mime_type and mime_type.startswith('image/'):
                file_type = 'image'
            elif ext in {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'} or (mime_type and (mime_type.startswith('application/vnd.') or mime_type == 'application/pdf')):
                file_type = 'office'
            elif ext in {'.txt', '.csv', '.json', '.html', '.htm', '.xml', '.yaml', '.yml'} or (mime_type and mime_type.startswith('text/')):
                file_type = 'document'
            else:
                self.logger.warning(f"Could not determine type for {attachment}")
                return content
            
            # Set target directory and relative path based on file type
            if file_type == 'image':
                target_dir = output_dir / 'images' / file_stem
                rel_path = f'images/{file_stem}/{attachment.name}'
            elif file_type == 'office':
                target_dir = output_dir / 'office' / file_stem
                rel_path = f'office/{file_stem}/{attachment.name}'
            else:  # document
                target_dir = output_dir / 'documents' / file_stem
                rel_path = f'documents/{file_stem}/{attachment.name}'
            
            # Create target directory and ensure parent directories exist
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / attachment.name
            
            # Remove any existing copies in other directories
            for dir_type in ['images', 'documents', 'office']:
                if dir_type != file_type.replace('document', 'documents'):
                    other_dir = output_dir / dir_type / file_stem
                    other_file = other_dir / attachment.name
                    if other_file.exists():
                        other_file.unlink()
                        self.logger.info(f"Removed duplicate file {other_file}")
            
            # Copy file if it doesn't exist
            if not target_file.exists():
                shutil.copy2(attachment, target_file)
                self.logger.info(f"Copied {attachment.name} to {target_file}")
            
            # Create markdown content for the attachment
            if file_type == 'image':
                markdown = f'\n![{attachment.stem}]({rel_path})\n'
            else:
                markdown = f'\n[{attachment.stem}]({rel_path})\n'
            
            # Add metadata if enabled
            if self.metadata_preservation:
                stats = attachment.stat()
                metadata = {
                    'type': mime_type or f'application/{file_type}',
                    'size': stats.st_size,
                    'modified': datetime.fromtimestamp(stats.st_mtime).isoformat()
                }
                markdown += f'<!-- {json.dumps(metadata)} -->\n'
            
            # Find any existing references to this attachment in the content
            # Match both relative and full paths
            attachment_name = re.escape(attachment.name)
            attachment_dir = re.escape(str(attachment.parent.name))
            attachment_patterns = [
                # Links with embed metadata
                rf'\[([^\]]*)\]\({attachment_name}\)<!-- \{{\"embed\":\"true\"\}} -->',  # Just filename
                rf'\[([^\]]*)\]\({attachment_dir}/{attachment_name}\)<!-- \{{\"embed\":\"true\"\}} -->',  # Dir/filename
                rf'\[([^\]]*)\]\({attachment_dir}%2F{attachment_name}\)<!-- \{{\"embed\":\"true\"\}} -->',  # URL encoded
                # Regular links
                rf'[^!]?\[([^\]]*)\]\({attachment_name}\)',  # Just filename
                rf'[^!]?\[([^\]]*)\]\({attachment_dir}/{attachment_name}\)',  # Dir/filename
                rf'[^!]?\[([^\]]*)\]\({attachment_dir}%2F{attachment_name}\)'  # URL encoded
            ]
            image_patterns = [
                # Image links with embed metadata
                rf'!\[([^\]]*)\]\({attachment_name}\)<!-- \{{\"embed\":\"true\"\}} -->',  # Just filename
                rf'!\[([^\]]*)\]\({attachment_dir}/{attachment_name}\)<!-- \{{\"embed\":\"true\"\}} -->',  # Dir/filename
                rf'!\[([^\]]*)\]\({attachment_dir}%2F{attachment_name}\)<!-- \{{\"embed\":\"true\"\}} -->',  # URL encoded
                # Regular image links
                rf'!\[([^\]]*)\]\({attachment_name}\)',  # Just filename
                rf'!\[([^\]]*)\]\({attachment_dir}/{attachment_name}\)',  # Dir/filename
                rf'!\[([^\]]*)\]\({attachment_dir}%2F{attachment_name}\)'  # URL encoded
            ]
            
            # Replace existing references with updated paths
            if file_type == 'image':
                for pattern in image_patterns:
                    if 'embed' in pattern:
                        content = re.sub(pattern, f'![\\1]({rel_path})<!-- {{"embed":"true"}} -->', content)
                    else:
                        content = re.sub(pattern, f'![\\1]({rel_path})', content)
            else:
                for pattern in attachment_patterns:
                    if 'embed' in pattern:
                        content = re.sub(pattern, f'[\\1]({rel_path})<!-- {{"embed":"true"}} -->', content)
                    else:
                        content = re.sub(pattern, f'[\\1]({rel_path})', content)
            
            # Only append new markdown if no existing reference was found
            has_reference = any(re.search(p, content) for p in attachment_patterns + image_patterns)
            if not has_reference:
                content += f"\n## Attachment: {attachment.name}\n{markdown}\n"
            
            return content
            
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