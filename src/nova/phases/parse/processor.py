"""Processor for the parse phase."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from ...core.errors import ProcessorError
from ...core.logging import get_logger
from ...core.config.base import HandlerConfig
from .handlers.markdown import MarkdownHandler, ConsolidationHandler

logger = get_logger(__name__)

class MarkdownProcessor:
    """Processor for markdown files in the parse phase."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the processor.
        
        Args:
            config: Optional configuration overrides
        """
        self.config = config or {}
        self.handlers = []
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Initialize handlers
        handler_configs = self.config.get('handlers', {})
        
        # Initialize MarkdownHandler if configured
        if 'MarkdownHandler' in handler_configs:
            handler = MarkdownHandler(handler_configs['MarkdownHandler'])
            self.handlers.append(handler)
            logger.info("Initialized MarkdownHandler")
            
        # Initialize ConsolidationHandler if configured
        if 'ConsolidationHandler' in handler_configs:
            handler = ConsolidationHandler(handler_configs['ConsolidationHandler'])
            self.handlers.append(handler)
            logger.info("Initialized ConsolidationHandler")
    
    async def process(self, file_path: Path, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process a markdown file.
        
        Args:
            file_path: Path to the markdown file
            context: Processing context
            
        Returns:
            Dict containing processed content and metadata
            
        Raises:
            ProcessorError: If processing fails
        """
        result = None
        
        try:
            # Get attachments directory
            attachments_dir = context.get('attachments_dir')
            attachments = []
            if attachments_dir and attachments_dir.exists():
                attachments = list(attachments_dir.glob('*'))
                logger.info(f"Found {len(attachments)} attachments in {attachments_dir}")
            
            # Find a handler that can process this file
            for handler in self.handlers:
                if handler.can_handle(file_path, attachments):
                    result = await handler.process(file_path, context, attachments)
                    break
                    
            if not result:
                raise ProcessorError(f"No handler found for {file_path}")
                
            return result
            
        except Exception as e:
            raise ProcessorError(f"Failed to process {file_path}: {str(e)}")
    
    async def cleanup(self) -> None:
        """Clean up processor resources."""
        for handler in self.handlers:
            await handler.cleanup() 