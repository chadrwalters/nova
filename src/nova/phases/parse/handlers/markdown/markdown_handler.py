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

from nova.phases.core.base_handler import BaseHandler
from nova.core.logging import get_logger

logger = get_logger(__name__)

class MarkitdownHandler(BaseHandler):
    """Handles markdown file processing."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the markdown handler.
        
        Args:
            config: Optional configuration overrides
        """
        super().__init__(config or {})
        
        # Configure markdown settings
        self.document_conversion = self.config.get('document_conversion', True)
        self.image_processing = self.config.get('image_processing', True)
        self.metadata_preservation = self.config.get('metadata_preservation', True)
        
    def can_handle(self, file_path: Path) -> bool:
        """Check if file can be processed.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            bool: True if file has markdown extension
        """
        return file_path.suffix.lower() in {'.md', '.markdown'}
        
    async def process(self, file_path: Path, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process markdown file.
        
        Args:
            file_path: Path to the markdown file
            context: Processing context
            
        Returns:
            Dict containing:
                - content: Processed markdown content
                - metadata: Extracted metadata
                - embedded_content: List of embedded content references
                - errors: List of processing errors
        """
        result = {
            'content': '',
            'metadata': {},
            'embedded_content': [],
            'errors': []
        }
        
        try:
            # Read file content
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # Extract frontmatter
            try:
                frontmatter_match = re.match(r'^\s*---\s*\n(.*?)\n\s*---\s*\n', content, re.DOTALL)
                if frontmatter_match:
                    frontmatter_str = frontmatter_match.group(1)
                    frontmatter = yaml.safe_load(frontmatter_str)
                    # Convert date objects to strings
                    for key, value in frontmatter.items():
                        if isinstance(value, (date, datetime)):
                            frontmatter[key] = value.isoformat()
                    result['metadata'].update(frontmatter)
                    content = content[frontmatter_match.end():]
            except yaml.YAMLError as e:
                result['errors'].append(str(e))
            
            # Update context with metadata
            context.update(result['metadata'])
            
            # Process embedded content
            if not context.get('embedded_content'):
                # Process markdown links with embed markers
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
                                    doc_file = context['attachments_dir'] / unquote(link_path)
                                else:
                                    doc_file = file_path.parent / unquote(link_path)
                                    
                                if doc_file.exists():
                                    try:
                                        async with aiofiles.open(doc_file, 'r', encoding='utf-8') as f:
                                            doc_content = await f.read()
                                        # Extract frontmatter from embedded document
                                        frontmatter_match = re.match(r'^\s*---\s*\n(.*?)\n\s*---\s*\n', doc_content, re.DOTALL)
                                        if frontmatter_match:
                                            frontmatter_str = frontmatter_match.group(1)
                                            doc_frontmatter = yaml.safe_load(frontmatter_str)
                                            # Convert date objects to strings
                                            for key, value in doc_frontmatter.items():
                                                if isinstance(value, (date, datetime)):
                                                    doc_frontmatter[key] = value.isoformat()
                                            doc_content = doc_content[frontmatter_match.end():]
                                        else:
                                            doc_frontmatter = {}
                                        result['embedded_content'].append({
                                            'type': 'document',
                                            'path': link_path,
                                            'metadata': doc_frontmatter,
                                            'content': doc_content
                                        })
                                        
                                        # Update the link path
                                        if context.get('output_attachments_dir'):
                                            new_path = str(Path(context['file_stem']) / doc_file.name)
                                            # Update the link with the new path
                                            old_link = match.group(0)  # Use the entire match
                                            new_link = f'[{link_text}]({quote(new_path)})'
                                            if match.group(3):  # If there was an embed marker
                                                new_link += match.group(3)
                                            line = line[:line_start + match.start()] + new_link + line[line_start + match.end():]
                                            
                                    except Exception as e:
                                        result['errors'].append(f"Error processing {link_path}: {str(e)}")
                                else:
                                    result['embedded_content'].append({
                                        'type': 'document',
                                        'path': link_path,
                                        'metadata': {},
                                        'content': ''
                                    })
                            
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
                                
                                # Update the image path
                                if context.get('output_attachments_dir'):
                                    new_path = str(Path(context['file_stem']) / image_path.name)
                                    # Update the image reference with the new path
                                    old_img = match.group(0)  # Use the entire match
                                    new_img = f'![{alt_text}]({quote(new_path)})'
                                    line = line[:line_start + match.start()] + new_img + line[line_start + match.end():]
                                    
                            line_start += match.start() + 1
                        except Exception as e:
                            result['errors'].append(f"Failed to process image: {str(e)}")
                            line_start += match.start() + 1
                    
                    content_lines[i] = line
                
                content = '\n'.join(content_lines)
                
                # Update context with embedded content
                context['embedded_content'] = result['embedded_content']
            else:
                # If we're running after consolidation handler, just use the context
                result['embedded_content'] = context['embedded_content']
            
            result['content'] = content
            return result
            
        except Exception as e:
            result['errors'].append(str(e))
            return result
            
    async def cleanup(self) -> None:
        """Clean up any resources."""
        pass 