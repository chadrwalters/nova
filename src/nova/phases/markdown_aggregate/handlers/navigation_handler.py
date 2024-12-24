"""Handler for adding navigation elements to aggregated content."""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import aiofiles

from .base_handler import BaseAggregateHandler
from ..config.defaults import DEFAULT_CONFIG

class NavigationHandler(BaseAggregateHandler):
    """Handles adding navigation elements to aggregated content."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the navigation handler.
        
        Args:
            config: Optional configuration overrides
        """
        super().__init__(config)
        
        # Merge default config with provided config
        self.config = {**DEFAULT_CONFIG.get('aggregate', {}).get('navigation', {}), **(config or {})}
        
        # Set up navigation templates
        self.templates = {
            'text': {
                'prev': '← Previous: [{title}]({link})',
                'next': 'Next: [{title}]({link}) →',
                'top': '[↑ Back to Top](#table-of-contents)'
            },
            'arrow': {
                'prev': '←',
                'next': '→',
                'top': '↑'
            }
        }
    
    def can_handle(self, files: List[Path]) -> bool:
        """Check if navigation can be added.
        
        Args:
            files: List of files to check
            
        Returns:
            bool: True if navigation can be added
        """
        return bool(files)  # Can add navigation if there are files
    
    async def process(self, files: List[Path], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process and add navigation.
        
        Args:
            files: List of files (not used directly)
            context: Processing context with content to modify
            
        Returns:
            Dict containing results with navigation
        """
        result = {
            'content': context.get('content', ''),
            'metadata': {
                'navigation': {
                    'sections': [],
                    'added_elements': []
                }
            },
            'file_map': context.get('file_map', {}),
            'errors': []
        }
        
        try:
            # Extract sections
            sections = self._extract_sections(result['content'])
            result['metadata']['navigation']['sections'] = [s['title'] for s in sections]
            
            # Add navigation elements
            result['content'] = self._add_navigation(
                content=result['content'],
                sections=sections
            )
            
        except Exception as e:
            result['errors'].append(f"Error adding navigation: {str(e)}")
            await self.rollback(result)
        
        return result
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate processing results.
        
        Args:
            result: Processing results to validate
            
        Returns:
            bool: True if results are valid
        """
        required_keys = {'content', 'metadata', 'file_map', 'errors'}
        return (
            all(key in result for key in required_keys) and
            isinstance(result['content'], str) and
            isinstance(result['metadata'], dict) and
            isinstance(result['file_map'], dict) and
            isinstance(result['errors'], list) and
            'navigation' in result['metadata']
        )
    
    async def rollback(self, result: Dict[str, Any]) -> None:
        """Rollback is not needed for navigation as it's non-destructive."""
        pass
    
    def _extract_sections(self, content: str) -> List[Dict[str, Any]]:
        """Extract sections and their titles from content."""
        sections = []
        
        # Find all section markers and titles
        start_pattern = r'<!-- START_FILE: (.+?) -->\n(.*?)<!-- END_FILE:'
        matches = re.finditer(start_pattern, content, re.DOTALL)
        
        for match in matches:
            filename = match.group(1)
            section_content = match.group(2)
            
            # Extract title from first heading or use filename
            title = self._extract_title(section_content) or filename
            
            sections.append({
                'filename': filename,
                'title': title,
                'start': match.start(),
                'end': match.end()
            })
        
        return sections
    
    def _extract_title(self, content: str) -> Optional[str]:
        """Extract title from first heading in content."""
        heading_pattern = r'^#\s+(.+)$'
        match = re.search(heading_pattern, content, re.MULTILINE)
        return match.group(1) if match else None
    
    def _add_navigation(self, content: str, sections: List[Dict[str, Any]]) -> str:
        """Add navigation elements to content."""
        style = self.config.get('link_style', 'text')
        position = self.config.get('position', 'bottom')
        templates = self.templates[style]
        
        # Process each section
        for i, section in enumerate(sections):
            nav_elements = []
            
            # Previous link
            if i > 0:
                prev_section = sections[i - 1]
                nav_elements.append(templates['prev'].format(
                    title=prev_section['title'],
                    link=f"#{self._make_anchor(prev_section['title'])}"
                ))
            
            # Top link
            if self.config.get('add_top_link', True):
                nav_elements.append(templates['top'])
            
            # Next link
            if i < len(sections) - 1:
                next_section = sections[i + 1]
                nav_elements.append(templates['next'].format(
                    title=next_section['title'],
                    link=f"#{self._make_anchor(next_section['title'])}"
                ))
            
            # Create navigation block
            if nav_elements:
                nav_block = '\n\n---\n' + ' | '.join(nav_elements) + '\n\n'
                
                # Add navigation based on position
                if position in ('top', 'both'):
                    content = content[:section['start']] + nav_block + content[section['start']:]
                if position in ('bottom', 'both'):
                    end_pos = content.find(f"<!-- END_FILE: {section['filename']} -->")
                    if end_pos != -1:
                        content = content[:end_pos] + nav_block + content[end_pos:]
        
        return content
    
    def _make_anchor(self, title: str) -> str:
        """Convert title to HTML anchor."""
        return re.sub(r'[^\w\s-]', '', title).lower().replace(' ', '-') 