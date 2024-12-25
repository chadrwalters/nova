"""Handler for consolidating markdown content with embedded content."""

from pathlib import Path
from typing import Dict, Any, List, Optional
import aiofiles
import yaml
import re
from datetime import date, datetime

from nova.phases.core.base_handler import BaseHandler
from ...config.defaults import DEFAULT_CONFIG

class ConsolidationHandler(BaseHandler):
    """Handles consolidation of markdown content with embedded content."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the consolidation handler.
        
        Args:
            config: Optional configuration overrides
        """
        super().__init__(config)
        
        # Merge default config with provided config
        self.config = {**DEFAULT_CONFIG.get('consolidation', {}), **(config or {})}
        
        # Configure consolidation settings
        self.sort_by_date = self.config.get('sort_by_date', True)
        self.preserve_headers = self.config.get('preserve_headers', True)
        
    def can_handle(self, file_path: Path, attachments: Optional[List[Path]] = None) -> bool:
        """Check if file can be consolidated.
        
        Args:
            file_path: Path to the file to check
            attachments: Optional list of attachments
            
        Returns:
            bool: True if file has markdown extension and has embedded content
        """
        if not file_path.suffix.lower() in {'.md', '.markdown'}:
            return False
            
        # Always return True since we want to process all markdown files
        return True
    
    async def process(
        self, 
        file_path: Path, 
        context: Dict[str, Any],
        attachments: Optional[List[Path]] = None
    ) -> Dict[str, Any]:
        """Process and consolidate markdown content.
        
        Args:
            file_path: Path to the markdown file
            context: Processing context
            attachments: Optional list of attachments to consolidate
            
        Returns:
            Dict containing:
                - content: Consolidated markdown content
                - metadata: Combined metadata
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
            # Read original content
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # Extract frontmatter if not already processed
            if not context.get('metadata'):
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
            else:
                result['metadata'].update(context['metadata'])
            
            # Process embedded content
            if not context.get('embedded_content'):
                # If we're running first, just identify embedded content
                embed_pattern = r'\{embed:\s*([^}]+)\}'
                for match in re.finditer(embed_pattern, content):
                    doc_path = match.group(1).strip()
                    doc_file = Path(file_path.parent, doc_path)
                    if not doc_file.exists():
                        result['errors'].append(f"Missing document file: {doc_path}")
                    result['embedded_content'].append({
                        'type': 'document',
                        'path': doc_path,
                        'metadata': {},
                        'content': ''  # Don't load content when running first
                    })
                
                img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
                for match in re.finditer(img_pattern, content):
                    alt_text = match.group(1)
                    img_path = match.group(2)
                    img_file = Path(file_path.parent, img_path)
                    if not img_file.exists():
                        result['errors'].append(f"Missing image file: {img_path}")
                    result['embedded_content'].append({
                        'type': 'image',
                        'path': img_path,
                        'alt': alt_text
                    })
                
                # Update context with embedded content
                context['embedded_content'] = result['embedded_content']
            else:
                # If we're running after markdown handler, process and load the content
                result['embedded_content'] = []  # Start with empty list to collect all content
                for item in context['embedded_content']:
                    if item['type'] == 'document':
                        doc_path = Path(file_path.parent, item['path'])
                        if doc_path.exists():
                            try:
                                async with aiofiles.open(doc_path, 'r', encoding='utf-8') as f:
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
                                    item['metadata'] = doc_frontmatter
                                    doc_content = doc_content[frontmatter_match.end():]
                                item['content'] = doc_content
                                result['metadata'].update(item['metadata'])
                                result['embedded_content'].append(item)
                                
                                # Look for embedded content within the embedded document
                                embed_pattern = r'\{embed:\s*([^}]+)\}'
                                for match in re.finditer(embed_pattern, doc_content):
                                    nested_doc_path = match.group(1).strip()
                                    nested_doc_file = Path(doc_path.parent, nested_doc_path)
                                    if not nested_doc_file.exists():
                                        result['errors'].append(f"Missing nested document file: {nested_doc_path}")
                                    result['embedded_content'].append({
                                        'type': 'document',
                                        'path': nested_doc_path,
                                        'metadata': {},
                                        'content': ''
                                    })
                                
                                # Look for images within the embedded document
                                img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
                                for match in re.finditer(img_pattern, doc_content):
                                    alt_text = match.group(1)
                                    img_path = match.group(2)
                                    img_file = Path(doc_path.parent, img_path)
                                    if not img_file.exists():
                                        result['errors'].append(f"Missing image file: {img_path}")
                                    result['embedded_content'].append({
                                        'type': 'image',
                                        'path': img_path,
                                        'alt': alt_text
                                    })
                            except Exception as e:
                                result['errors'].append(f"Error processing {item['path']}: {str(e)}")
                        else:
                            result['errors'].append(f"Missing document file: {item['path']}")
                    elif item['type'] == 'image':
                        img_path = Path(file_path.parent, item['path'])
                        if not img_path.exists():
                            result['errors'].append(f"Missing image file: {item['path']}")
                        result['embedded_content'].append(item)
                
                # Update context with expanded embedded content
                context['embedded_content'] = result['embedded_content']
            
            result['content'] = content
            return result
            
        except Exception as e:
            result['errors'].append(str(e))
            return result
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate processing results.
        
        Args:
            result: Results to validate
            
        Returns:
            bool: True if results are valid
        """
        required_keys = {'content', 'metadata', 'embedded_content', 'errors'}
        return (
            all(key in result for key in required_keys) and
            isinstance(result['content'], str) and
            isinstance(result['metadata'], dict) and
            isinstance(result['embedded_content'], list) and
            isinstance(result['errors'], list)
        )
    
    def _merge_content(self, original: str, attachment_content: str) -> str:
        """Merge original content with attachment content."""
        if self.sort_by_date:
            # TODO: Implement date-based sorting
            pass
            
        if self.preserve_headers:
            # Ensure blank line after headers
            original = original.rstrip() + "\n\n"
            
        return original + attachment_content 