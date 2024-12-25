"""Document handling components for Nova processors."""

from pathlib import Path
from typing import Dict, Any, Optional, List
import aiofiles

from .base import BaseHandler
from ..errors import ProcessingError

class DocumentHandler(BaseHandler):
    """Handles document processing and conversion."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize document handler.
        
        Args:
            config: Handler configuration
        """
        super().__init__(config)
        self.config = config or {}
    
    def can_handle(self, file_path: Path) -> bool:
        """Check if file can be handled.
        
        Args:
            file_path: Path to check
            
        Returns:
            bool: True if file is a document type
        """
        return file_path.suffix.lower() in {'.md', '.txt', '.doc', '.docx'}
    
    async def process(self, input_path: Path, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process document file.
        
        Args:
            input_path: Path to input file
            context: Processing context
            
        Returns:
            Dict containing:
                - content: Processed content
                - errors: List of processing errors
        """
        result = {
            'content': '',
            'errors': []
        }
        
        try:
            # Read document content
            async with aiofiles.open(input_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                
            # Store processed content
            result['content'] = content
            
        except Exception as e:
            error = f"Failed to process document {input_path}: {str(e)}"
            result['errors'].append(error)
        
        return result