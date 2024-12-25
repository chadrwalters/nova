"""Handler for consolidating markdown files and attachments."""

from pathlib import Path
from typing import Dict, Any, Optional, List
import re
import shutil
import os
import json
from urllib.parse import unquote, quote
import aiofiles
import logging
from datetime import datetime

from nova.phases.core.base_handler import BaseHandler, HandlerResult
from nova.core.logging import get_logger

logger = get_logger(__name__)

class ConsolidationHandler(BaseHandler):
    """Handles consolidation of markdown files."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the consolidation handler.
        
        Args:
            config: Optional configuration overrides
        """
        super().__init__(config)
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Configure processing options
        self.sort_by_date = self.get_option('sort_by_date', True)
        self.preserve_headers = self.get_option('preserve_headers', True)
    
    def can_handle(self, file_path: Path, attachments: Optional[List[Path]] = None) -> bool:
        """Check if file can be consolidated.
        
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
    ) -> HandlerResult:
        """Process and consolidate markdown file.
        
        Args:
            file_path: Path to the markdown file
            context: Processing context
            attachments: Optional list of attachments
            
        Returns:
            HandlerResult containing processed content and metadata
        """
        result = HandlerResult()
        result.start_time = datetime.now()
        
        try:
            # Read and parse markdown file
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                
            # Process embedded content
            if attachments:
                for attachment in attachments:
                    embed_config = context.get('embed_config', {})
                    if embed_config.get('embed') == 'true':
                        content = await self._process_attachment(content, attachment)
                        
            # Update result
            result.content = content
            result.processed_files.append(file_path)
            if attachments:
                result.processed_attachments.extend(attachments)
                
        except Exception as e:
            result.add_error(f"Failed to process {file_path}: {str(e)}")
            
        finally:
            result.end_time = datetime.now()
            if result.start_time:
                result.processing_time = (result.end_time - result.start_time).total_seconds()
            
        return result
    
    async def _process_attachment(self, content: str, attachment: Path) -> str:
        """Process an attachment and update content accordingly."""
        # Add attachment processing logic here
        return content
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate the processing results.
        
        Args:
            result: The processing results to validate
            
        Returns:
            bool: True if results are valid
        """
        required_keys = {'content', 'processed_files', 'processed_attachments', 'errors'}
        return all(key in result for key in required_keys) 