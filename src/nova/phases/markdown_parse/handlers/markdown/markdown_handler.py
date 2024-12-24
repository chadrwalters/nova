"""Handler for processing markdown files."""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from markitdown import MarkdownParser  # type: ignore

from ..base_handler import BaseHandler
from ...config.defaults import DEFAULT_CONFIG

class MarkdownHandler(BaseHandler):
    """Handles parsing and processing of markdown files."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the markdown handler.
        
        Args:
            config: Optional configuration overrides
        """
        super().__init__(config)
        self.parser = MarkdownParser()
        self.supported_extensions = {'.md', '.markdown', '.mdown', '.mkdn'}
        
        # Merge default config with provided config
        self.config = {**DEFAULT_CONFIG.get('markdown', {}), **(config or {})}
    
    def can_handle(self, file_path: Path) -> bool:
        """Check if file is a markdown file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            bool: True if file has markdown extension
        """
        return file_path.suffix.lower() in self.supported_extensions
    
    async def process(self, file_path: Path, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process a markdown file.
        
        Args:
            file_path: Path to the markdown file
            context: Processing context
            
        Returns:
            Dict containing:
                - content: Processed markdown content
                - metadata: Extracted metadata
                - links: List of found links
                - images: List of found images
                - errors: List of processing errors
        """
        result = {
            'content': '',
            'metadata': {},
            'links': [],
            'images': [],
            'errors': []
        }
        
        try:
            # Read and parse markdown
            content = await self._read_file(file_path)
            parsed = self.parser.parse(content)
            
            # Extract metadata if present
            result['metadata'] = self._extract_metadata(parsed)
            
            # Process content
            result['content'] = self._process_content(parsed)
            
            # Find links and images
            result['links'] = self._extract_links(result['content'])
            result['images'] = self._extract_images(result['content'])
            
        except Exception as e:
            result['errors'].append(str(e))
        
        return result
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate processing results.
        
        Args:
            result: Processing results to validate
            
        Returns:
            bool: True if results are valid
        """
        required_keys = {'content', 'metadata', 'links', 'images', 'errors'}
        return (
            all(key in result for key in required_keys) and
            isinstance(result['content'], str) and
            isinstance(result['metadata'], dict) and
            isinstance(result['links'], list) and
            isinstance(result['images'], list) and
            isinstance(result['errors'], list)
        )
    
    async def _read_file(self, file_path: Path) -> str:
        """Read markdown file content."""
        async with open(file_path, 'r', encoding='utf-8') as f:
            return await f.read()
    
    def _extract_metadata(self, parsed: Any) -> Dict[str, Any]:
        """Extract metadata from parsed markdown."""
        metadata = {}
        if hasattr(parsed, 'metadata'):
            metadata = parsed.metadata
        return metadata
    
    def _process_content(self, parsed: Any) -> str:
        """Process parsed markdown content."""
        if self.config.get('preserve_formatting', True):
            return str(parsed)
        return parsed.to_plain_text()
    
    def _extract_links(self, content: str) -> List[Dict[str, str]]:
        """Extract links from markdown content."""
        links = []
        link_pattern = r'\[([^\]]*)\]\(([^)]+)\)'
        for match in re.finditer(link_pattern, content):
            links.append({
                'text': match.group(1),
                'url': match.group(2)
            })
        return links
    
    def _extract_images(self, content: str) -> List[Dict[str, str]]:
        """Extract images from markdown content."""
        images = []
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        for match in re.finditer(image_pattern, content):
            images.append({
                'alt': match.group(1),
                'src': match.group(2)
            })
        return images 