"""Handler for processing markdown files."""

from pathlib import Path
from typing import Dict, Any, List, Optional
import aiofiles
import yaml
import re
from datetime import date, datetime

from nova.phases.core.base_handler import BaseHandler
from ...config.defaults import DEFAULT_CONFIG

class MarkitdownHandler(BaseHandler):
    """Handles markdown file processing."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the markdown handler.
        
        Args:
            config: Optional configuration overrides
        """
        super().__init__(config)
        
        # Merge default config with provided config
        self.config = {**DEFAULT_CONFIG.get('markdown', {}), **(config or {})}
        
        # Configure markdown settings
        self.document_conversion = self.config.get('document_conversion', True)
        self.image_processing = self.config.get('image_processing', True)
        self.metadata_preservation = self.config.get('metadata_preservation', True)
        
    def can_handle(self, file_path: Path, attachments: Optional[List[Path]] = None) -> bool:
        """Check if file can be processed.
        
        Args:
            file_path: Path to the file to check
            attachments: Optional list of attachments
            
        Returns:
            bool: True if file has markdown extension
        """
        return file_path.suffix.lower() in {'.md', '.markdown'}

    async def process(
        self, 
        file_path: Path, 
        context: Dict[str, Any],
        attachments: Optional[List[Path]] = None
    ) -> Dict[str, Any]:
        """Process markdown file.
        
        Args:
            file_path: Path to the markdown file
            context: Processing context
            attachments: Optional list of attachments to process
            
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
                # If we're running first, process all embedded content
                embed_pattern = r'\{embed:\s*([^}]+)\}'
                for match in re.finditer(embed_pattern, content):
                    doc_path = match.group(1).strip()
                    doc_file = Path(file_path.parent, doc_path)
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
                                'path': doc_path,
                                'metadata': doc_frontmatter,
                                'content': doc_content
                            })
                            # Look for nested embedded content
                            for nested_match in re.finditer(embed_pattern, doc_content):
                                nested_doc_path = nested_match.group(1).strip()
                                result['embedded_content'].append({
                                    'type': 'document',
                                    'path': nested_doc_path,
                                    'metadata': {},
                                    'content': ''
                                })
                        except Exception as e:
                            result['errors'].append(f"Error processing {doc_path}: {str(e)}")
                    else:
                        result['embedded_content'].append({
                            'type': 'document',
                            'path': doc_path,
                            'metadata': {},
                            'content': ''
                        })
                
                # Extract image references
                img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
                for match in re.finditer(img_pattern, content):
                    alt_text = match.group(1)
                    img_path = match.group(2)
                    result['embedded_content'].append({
                        'type': 'image',
                        'path': img_path,
                        'alt': alt_text
                    })
                    # Track image in context
                    if not context.get('images'):
                        context['images'] = []
                    context['images'].append(Path(img_path).name)
                
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