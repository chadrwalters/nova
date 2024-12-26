"""Handler for text files."""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

from .....core.handlers.base import BaseHandler
from .....core.logging import get_logger

logger = get_logger(__name__)

class TextHandler(BaseHandler):
    """Handles processing of text files."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the text handler.
        
        Args:
            config: Optional configuration overrides
        """
        super().__init__(config)
        
        self.supported_formats = {
            '.txt', '.text', '.log', '.csv', '.json', '.yaml', '.yml'
        }
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
    
    async def can_handle(self, file_path: Path) -> bool:
        """Check if file is a supported text format.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            bool: True if file is a supported text format
        """
        return file_path.suffix.lower() in self.supported_formats
    
    async def process(self, file_path: Path, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process a text file.
        
        Args:
            file_path: Path to the text file
            context: Processing context
            
        Returns:
            Dict containing:
                - content: Text content
                - metadata: File metadata
                - format: File format
                - errors: List of processing errors
        """
        result = {
            'content': '',
            'metadata': {},
            'format': file_path.suffix.lower(),
            'errors': []
        }
        
        try:
            # Read content
            content = file_path.read_text(encoding='utf-8')
            result['content'] = content
            
            # Extract metadata
            result['metadata'].update({
                'file_size': file_path.stat().st_size,
                'modified_time': file_path.stat().st_mtime,
                'created_time': file_path.stat().st_ctime
            })
            
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
        required_keys = {'content', 'metadata', 'format', 'errors'}
        return (
            all(key in result for key in required_keys) and
            isinstance(result['content'], str) and
            isinstance(result['metadata'], dict) and
            isinstance(result['format'], str) and
            isinstance(result['errors'], list)
        )
    
    async def cleanup(self) -> None:
        """Clean up any resources used by the handler."""
        pass 