"""Handler for validating links in markdown files."""

# Standard library imports
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

# Nova package imports
from nova.core.base_handler import BaseHandler
from nova.core.models.result import ProcessingResult


class LinkValidator(BaseHandler):
    """Handler for validating links in markdown files."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the handler.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        
        # Initialize link patterns
        self.link_patterns = {
            'markdown': r'\[([^\]]+)\]\(([^)]+)\)',
            'html': r'<a\s+(?:[^>]*?\s+)?href="([^"]*)"',
            'image': r'!\[([^\]]*)\]\(([^)]+)\)'
        }
    
    async def can_handle(self, file_path: Path) -> bool:
        """Check if this handler can process the file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if this handler can process the file, False otherwise
        """
        return file_path.suffix.lower() == '.md'
    
    async def process(self, file_path: Path, context: Dict[str, Any]) -> ProcessingResult:
        """Process a markdown file.
        
        Args:
            file_path: Path to the file to process
            context: Processing context
            
        Returns:
            ProcessingResult containing processed content and metadata
        """
        try:
            # Initialize result
            result = ProcessingResult()
            result.input_file = file_path
            result.output_dir = Path(context.get('output_dir', ''))
            
            # Read content
            content = file_path.read_text()
            
            # Find and validate links
            links = self._find_links(content)
            valid_links = []
            invalid_links = []
            
            for link in links:
                if self._validate_link(link):
                    valid_links.append(link)
                else:
                    invalid_links.append(link)
            
            # Create output file
            output_file = result.output_dir / file_path.name
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(content)
            
            # Update result
            result.success = len(invalid_links) == 0
            result.output_files.append(output_file)
            result.content = content
            result.metadata = {
                'links': {
                    'total': len(links),
                    'valid': len(valid_links),
                    'invalid': len(invalid_links),
                    'valid_links': valid_links,
                    'invalid_links': invalid_links
                }
            }
            
            # Add errors for invalid links
            for link in invalid_links:
                error_msg = f"Invalid link found: {link}"
                result.errors.append(error_msg)
                if self.monitoring:
                    self.monitoring.record_error(error_msg)
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to process file {file_path}: {str(e)}"
            self.logger.error(error_msg)
            if self.monitoring:
                self.monitoring.record_error(error_msg)
            raise ValidationError(error_msg)
    
    def _find_links(self, content: str) -> List[str]:
        """Find all links in content.
        
        Args:
            content: Content to search
            
        Returns:
            List of found links
        """
        links = []
        
        # Search for each link type
        for pattern in self.link_patterns.values():
            matches = re.finditer(pattern, content)
            for match in matches:
                # Get link URL from match
                if len(match.groups()) > 1:
                    links.append(match.group(2))  # Markdown/image links
                else:
                    links.append(match.group(1))  # HTML links
        
        return links
    
    def _validate_link(self, link: str) -> bool:
        """Validate a link.
        
        Args:
            link: Link to validate
            
        Returns:
            True if link is valid, False otherwise
        """
        # Skip anchor links
        if link.startswith('#'):
            return True
            
        # Skip external links
        if link.startswith(('http://', 'https://', 'mailto:', 'tel:')):
            return True
            
        # Check if local file exists
        path = Path(link)
        return path.exists()
    
    def validate_output(self, result: ProcessingResult) -> bool:
        """Validate the processing results.
        
        Args:
            result: The ProcessingResult to validate
            
        Returns:
            True if results are valid, False otherwise
        """
        return result.success and bool(result.content)
    
    async def rollback(self, result: ProcessingResult) -> None:
        """Roll back any changes made during processing.
        
        Args:
            result: The ProcessingResult to roll back
        """
        # No changes to roll back for this handler
        pass 