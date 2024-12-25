"""Handler for consolidating markdown files and attachments."""

from pathlib import Path
from typing import Dict, Any, Optional, List
import re
import shutil
import os
import json
from urllib.parse import unquote, quote

from nova.phases.core.base_handler import BaseHandler
from nova.core.logging import get_logger

logger = get_logger(__name__)

class ConsolidationHandler(BaseHandler):
    """Handles consolidation of markdown files and their attachments."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the consolidation handler.
        
        Args:
            config: Optional configuration overrides
        """
        super().__init__(config or {})
        self.sort_by_date = self.config.get('sort_by_date', True)
        self.preserve_headers = self.config.get('preserve_headers', True)
        
    def can_handle(self, file_path: Path) -> bool:
        """Check if file can be processed.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            bool: True if file has markdown extension
        """
        return file_path.suffix.lower() in {'.md', '.markdown'}
        
    async def process(self, file_path: Path, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process markdown file and its attachments.
        
        Args:
            file_path: Path to the markdown file
            context: Processing context
            
        Returns:
            Dict containing:
                - content: Processed markdown content
                - errors: List of processing errors
        """
        result = {
            'content': context.get('content', ''),
            'errors': []
        }
        
        try:
            content = result['content']
            
            # Process embedded content markers
            embed_pattern = r'\[([^\]]+)\]\(([^)]+)\)(<!-- (\{.*?\}) -->)?'
            content_lines = content.split('\n')
            for i, line in enumerate(content_lines):
                line_start = 0
                while True:
                    match = re.search(embed_pattern, line[line_start:])
                    if not match:
                        break
                        
                    try:
                        link_text = match.group(1)
                        link_path = unquote(match.group(2))
                        embed_config = json.loads(match.group(4)) if match.group(4) else {}
                        
                        if embed_config.get('embed') == 'true':
                            # Resolve the attachment path
                            if context.get('attachments_dir'):
                                attachment_path = context['attachments_dir'] / unquote(link_path)
                            else:
                                attachment_path = file_path.parent / unquote(link_path)
                                
                            if attachment_path.exists():
                                # Copy the file if not already copied
                                if context.get('output_attachments_dir'):
                                    output_path = context['output_attachments_dir'] / attachment_path.name
                                    if not output_path.exists():
                                        shutil.copy2(attachment_path, output_path)
                                        logger.info(f"Copied attachment: {attachment_path.name}")
                                
                                # Update the link path
                                if context.get('output_attachments_dir'):
                                    new_path = str(Path(context['file_stem']) / attachment_path.name)
                                    # Update the link with the new path
                                    old_link = match.group(0)  # Use the entire match
                                    new_link = f'[{link_text}]({quote(new_path)})'
                                    if match.group(3):  # If there was an embed marker
                                        new_link += match.group(3)
                                    line = line[:line_start + match.start()] + new_link + line[line_start + match.end():]
                                    logger.info(f"Updated link: {old_link} -> {new_link}")
                                    
                        line_start += match.start() + 1
                    except json.JSONDecodeError as e:
                        result['errors'].append(f"Invalid embed config: {str(e)}")
                    except Exception as e:
                        result['errors'].append(f"Failed to process embed: {str(e)}")
                        line_start += match.start() + 1
                
                content_lines[i] = line
            
            # Process image references
            img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
            for i, line in enumerate(content_lines):
                line_start = 0
                while True:
                    match = re.search(img_pattern, line[line_start:])
                    if not match:
                        break
                        
                    try:
                        alt_text = match.group(1)
                        img_path = unquote(match.group(2))
                        
                        # Skip data URIs
                        if img_path.startswith('data:'):
                            line_start += match.start() + 1
                            continue
                            
                        # Resolve the image path
                        if context.get('attachments_dir'):
                            image_path = context['attachments_dir'] / unquote(img_path)
                        else:
                            image_path = file_path.parent / unquote(img_path)
                            
                        if image_path.exists():
                            # Copy the file if not already copied
                            if context.get('output_attachments_dir'):
                                output_path = context['output_attachments_dir'] / image_path.name
                                if not output_path.exists():
                                    shutil.copy2(image_path, output_path)
                                    logger.info(f"Copied image: {image_path.name}")
                            
                            # Update the image path
                            if context.get('output_attachments_dir'):
                                new_path = str(Path(context['file_stem']) / image_path.name)
                                # Update the image reference with the new path
                                old_img = match.group(0)  # Use the entire match
                                new_img = f'![{alt_text}]({quote(new_path)})'
                                line = line[:line_start + match.start()] + new_img + line[line_start + match.end():]
                                logger.info(f"Updated image reference: {old_img} -> {new_img}")
                                
                        line_start += match.start() + 1
                    except Exception as e:
                        result['errors'].append(f"Failed to process image: {str(e)}")
                        line_start += match.start() + 1
                
                content_lines[i] = line
            
            result['content'] = '\n'.join(content_lines)
            return result
            
        except Exception as e:
            error = f"Failed to process file {file_path}: {str(e)}"
            result['errors'].append(error)
            logger.error(error)
            return result
            
    async def cleanup(self) -> None:
        """Clean up any resources."""
        pass 