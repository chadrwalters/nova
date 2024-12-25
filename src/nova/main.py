"""Main entry point for Nova document processor."""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from .core.errors import ProcessorError
from .core.logging import get_logger
from .core.config.base import HandlerConfig
from .phases.parse import MarkdownProcessor

logger = get_logger(__name__)

async def process_documents(config: Optional[Dict[str, Any]] = None) -> bool:
    """Process documents through the pipeline.
    
    Args:
        config: Optional configuration overrides
        
    Returns:
        bool: True if processing completed successfully
    """
    try:
        # Initialize processor with configuration
        processor_config = {
            'handlers': {
                'MarkdownHandler': HandlerConfig(
                    type='MarkdownHandler',
                    base_handler='nova.phases.core.base_handler.BaseHandler',
                    document_conversion=True,
                    image_processing=True,
                    metadata_preservation=True
                ),
                'ConsolidationHandler': HandlerConfig(
                    type='ConsolidationHandler',
                    base_handler='nova.phases.core.base_handler.BaseHandler',
                    sort_by_date=True,
                    preserve_headers=True
                )
            }
        }
        
        processor = MarkdownProcessor(processor_config)
        
        # Process each file
        for file_path in Path(config['input_dir']).glob('**/*.md'):
            # Set up context with embed configuration
            context = {
                'file_stem': file_path.stem,
                'output_dir': config['output_dir'],
                'attachments_dir': file_path.parent / file_path.stem if (file_path.parent / file_path.stem).exists() else None,
                'embed_config': {'embed': 'true'},  # Default to embedding content
                'phase': 'parse',
                'file_path': file_path,
                'base_dir': file_path.parent,
                'output_base': Path(config['output_dir'])
            }
            
            # Process the file
            logger.info(f"Processing {file_path}")
            result = await processor.process(file_path, context)
            
            # Log processing results
            if result:
                if result.errors:
                    for error in result.errors:
                        logger.error(f"Error processing {file_path}: {error}")
                else:
                    logger.info(f"Successfully processed {file_path}")
                    if result.processed_attachments:
                        logger.info(f"Processed {len(result.processed_attachments)} attachments")
            
        return True
        
    except Exception as e:
        logger.error(f"Failed to process documents: {str(e)}")
        return False 