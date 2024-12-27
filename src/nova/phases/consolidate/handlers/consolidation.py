"""Handler for consolidating markdown files with their attachments."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import re

from ....core.base_handler import BaseHandler
from ....core.models.result import ProcessingResult


class ConsolidationHandler(BaseHandler):
    """Handler for consolidating markdown files with their attachments."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the handler.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        
        # Initialize attachment patterns
        self.attachment_patterns = {
            'image': r'!\[.*?\]\((.*?)\)',
            'link': r'\[.*?\]\((.*?)\)'
        }
    
    async def can_handle(self, file_path: Path) -> bool:
        """Check if this handler can process the file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if this handler can process the file, False otherwise
        """
        return file_path.suffix.lower() == '.md'
    
    async def process(self, file_path: Path, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process a markdown file.
        
        Args:
            file_path: Path to the file to process
            context: Optional processing context
            
        Returns:
            ProcessingResult containing consolidated content and metadata
        """
        try:
            # Read input file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract attachments
            attachments = self._extract_attachments(content)
            
            # Create result
            result = ProcessingResult(
                success=True,
                content=content,
                metadata={'attachments': attachments}
            )
            result.add_processed_file(file_path)
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            return ProcessingResult(success=False, errors=[error_msg])
    
    def _extract_attachments(self, content: str) -> List[str]:
        """Extract attachment paths from markdown content.
        
        Args:
            content: Content to extract attachments from
            
        Returns:
            List of attachment paths
        """
        attachments = []
        
        # Extract image and link paths
        for pattern in self.attachment_patterns.values():
            matches = re.finditer(pattern, content)
            for match in matches:
                path = match.group(1)
                if path and path not in attachments:
                    attachments.append(path)
        
        return attachments
    
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