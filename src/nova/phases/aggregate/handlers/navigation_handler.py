"""Handler for adding navigation elements to aggregated content."""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import aiofiles

from nova.phases.core.base_handler import BaseHandler

class NavigationHandler(BaseHandler):
    """Handles adding navigation elements to aggregated content."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the navigation handler.
        
        Args:
            config: Optional configuration overrides
        """
        super().__init__(config)
        self.config = config or {}
        
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
        
        # Configure navigation
        self.link_style = self.config.get('link_style', 'text')
        self.position = self.config.get('position', 'bottom')
        self.add_top_link = self.config.get('add_top_link', True)
    
    def can_handle(self, file_path: Path, attachments: Optional[List[Path]] = None) -> bool:
        """Check if navigation can be added.
        
        Args:
            file_path: Path to the file to check
            attachments: Optional list of attachments (not used)
            
        Returns:
            bool: True if file is markdown
        """
        return file_path.suffix.lower() in {'.md', '.markdown'}
    
    async def process(
        self, 
        file_path: Path, 
        context: Dict[str, Any],
        attachments: Optional[List[Path]] = None
    ) -> Dict[str, Any]:
        """Process and add navigation.
        
        Args:
            file_path: Path to the markdown file
            context: Processing context
            attachments: Optional list of attachments (not used)
            
        Returns:
            Dict containing:
                - content: Content with added navigation
                - metadata: Navigation metadata
                - processed_attachments: Empty list
                - errors: List of processing errors
        """
        result = {
            'content': '',
            'metadata': {
                'navigation': {
                    'sections': [],
                    'added_elements': []
                }
            },
            'processed_attachments': [],
            'errors': []
        }
        
        try:
            # Read content if not provided in context
            content = context.get('content')
            if not content:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
            
            # Extract sections
            sections = self._extract_sections(content)
            result['metadata']['navigation']['sections'] = [s['title'] for s in sections]
            
            # Add navigation elements
            result['content'] = self._add_navigation(content, sections)
            
        except Exception as e:
            result['errors'].append(f"Error adding navigation: {str(e)}")
        
        return result
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate processing results.
        
        Args:
            result: Processing results to validate
            
        Returns:
            bool: True if results are valid
        """
        required_keys = {'content', 'metadata', 'processed_attachments', 'errors'}
        return (
            all(key in result for key in required_keys) and
            isinstance(result['content'], str) and
            isinstance(result['metadata'], dict) and
            isinstance(result['processed_attachments'], list) and
            isinstance(result['errors'], list) and
            'navigation' in result['metadata']
        )
    
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
        templates = self.templates[self.link_style]
        
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
            if self.add_top_link:
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
                if self.position in ('top', 'both'):
                    content = content[:section['start']] + nav_block + content[section['start']:]
                if self.position in ('bottom', 'both'):
                    end_pos = content.find(f"<!-- END_FILE: {section['filename']} -->")
                    if end_pos != -1:
                        content = content[:end_pos] + nav_block + content[end_pos:]
        
        return content
    
    def _make_anchor(self, title: str) -> str:
        """Convert title to HTML anchor."""
        return re.sub(r'[^\w\s-]', '', title).lower().replace(' ', '-') 