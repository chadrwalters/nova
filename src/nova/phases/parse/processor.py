"""Processor for the parse phase."""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

from ...core.errors import ProcessorError
from ...core.logging import get_logger
from ...core.config.base import HandlerConfig
from ...core.pipeline.base import BaseProcessor
from ...core.config import PipelineConfig, ProcessorConfig
from .handlers.markdown import MarkdownHandler, ConsolidationHandler

logger = get_logger(__name__)

class MarkdownProcessor(BaseProcessor):
    """Processor for markdown files in the parse phase."""
    
    def __init__(self, processor_config: Union[ProcessorConfig, Dict[str, Any]], pipeline_config: PipelineConfig):
        """Initialize the processor.
        
        Args:
            processor_config: Processor configuration
            pipeline_config: Pipeline configuration
        """
        super().__init__(processor_config, pipeline_config)
        self.handlers = []
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Initialize handlers from components
        if isinstance(processor_config, ProcessorConfig):
            # Get handlers from components
            for component_name, component in processor_config.components.items():
                if component.handlers:
                    for handler_config in component.handlers:
                        if handler_config.type == 'MarkdownHandler':
                            config = {
                                'base_dir': str(Path(os.environ.get('NOVA_BASE_DIR'))),
                                'input_dir': str(Path(os.environ.get('NOVA_INPUT_DIR'))),
                                'output_dir': str(Path(os.environ.get('NOVA_PHASE_MARKDOWN_PARSE'))),
                                'analyze_images': handler_config.image_processing
                            }
                            handler = MarkdownHandler(config)
                            self.handlers.append(handler)
                            logger.info("Initialized MarkdownHandler from components")
                        elif handler_config.type == 'ConsolidationHandler':
                            config = {
                                'base_dir': str(Path(os.environ.get('NOVA_BASE_DIR'))),
                                'input_dir': str(Path(os.environ.get('NOVA_INPUT_DIR'))),
                                'output_dir': str(Path(os.environ.get('NOVA_PHASE_MARKDOWN_PARSE')))
                            }
                            handler = ConsolidationHandler(config)
                            self.handlers.append(handler)
                            logger.info("Initialized ConsolidationHandler from components")
            
            # Get handlers from handler configs
            for handler_config in processor_config.handlers:
                if handler_config.type == 'MarkdownHandler':
                    config = {
                        'base_dir': str(Path(os.environ.get('NOVA_BASE_DIR'))),
                        'input_dir': str(Path(os.environ.get('NOVA_INPUT_DIR'))),
                        'output_dir': str(Path(os.environ.get('NOVA_PHASE_MARKDOWN_PARSE'))),
                        'analyze_images': handler_config.image_processing
                    }
                    handler = MarkdownHandler(config)
                    self.handlers.append(handler)
                    logger.info("Initialized MarkdownHandler from handler config")
                elif handler_config.type == 'ConsolidationHandler':
                    config = {
                        'base_dir': str(Path(os.environ.get('NOVA_BASE_DIR'))),
                        'input_dir': str(Path(os.environ.get('NOVA_INPUT_DIR'))),
                        'output_dir': str(Path(os.environ.get('NOVA_PHASE_MARKDOWN_PARSE')))
                    }
                    handler = ConsolidationHandler(config)
                    self.handlers.append(handler)
                    logger.info("Initialized ConsolidationHandler from handler config")
        else:
            # Handle dictionary config
            handler_configs = processor_config.get('components', {}).get('handlers', {})
            for handler_type, handler_config in handler_configs.items():
                if isinstance(handler_config, dict):
                    handler_config['base_dir'] = str(Path(os.environ.get('NOVA_BASE_DIR')))
                    handler_config['input_dir'] = str(Path(os.environ.get('NOVA_INPUT_DIR')))
                    handler_config['output_dir'] = str(Path(os.environ.get('NOVA_PHASE_MARKDOWN_PARSE')))
                    
                    if handler_type == 'MarkdownHandler':
                        handler = MarkdownHandler(handler_config)
                        self.handlers.append(handler)
                        logger.info("Initialized MarkdownHandler from dict config")
                    elif handler_type == 'ConsolidationHandler':
                        handler = ConsolidationHandler(handler_config)
                        self.handlers.append(handler)
                        logger.info("Initialized ConsolidationHandler from dict config")
    
    async def setup(self) -> bool:
        """Set up the processor.
        
        Returns:
            True if setup was successful, False otherwise
        """
        try:
            # Get input directory
            self.input_dir = Path(os.environ.get('NOVA_INPUT_DIR'))
            if not self.input_dir.exists():
                logger.error(f"Input directory not found: {self.input_dir}")
                return False
                
            # Get output directory
            self.output_dir = Path(os.environ.get('NOVA_PHASE_MARKDOWN_PARSE'))
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Find markdown files recursively
            self.markdown_files = list(self.input_dir.rglob('*.md'))
            logger.info(f"Found {len(self.markdown_files)} markdown files in {self.input_dir}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set up processor: {str(e)}")
            return False
    
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