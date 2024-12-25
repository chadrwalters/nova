"""Main entry point for Nova document processor."""

import asyncio
import os
from pathlib import Path
from typing import Dict, Any, Optional

from .core.config import load_config, ProcessorConfig, ComponentConfig
from .core.logging import get_logger
from .core.errors import PipelineError
from .core.pipeline.manager import PipelineManager
from .phases.parse.processor import MarkdownProcessor
from .phases.consolidate.processor import MarkdownConsolidateProcessor
from .phases.aggregate.processor import MarkdownAggregateProcessor
from .phases.split.processor import ThreeFileSplitProcessor

logger = get_logger(__name__)

async def process_documents(
    input_dir: str,
    output_dir: str,
    start_phase: Optional[str] = None,
    end_phase: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None
) -> bool:
    """Process documents through the pipeline.
    
    Args:
        input_dir: Input directory path
        output_dir: Output directory path
        start_phase: Optional phase to start from
        end_phase: Optional phase to end at
        options: Optional processing options
        
    Returns:
        True if processing completed successfully, False otherwise
    """
    try:
        # Load configuration
        config = load_config()
        config.input_dir = input_dir
        config.output_dir = output_dir
        
        # Set up pipeline manager
        pipeline = PipelineManager(config)
        
        # Get components from config
        components = {}
        if hasattr(config, 'pipeline') and 'components' in config.pipeline:
            components = config.pipeline['components']
            if not isinstance(components, dict):
                components = {}
        
        # Create processor configs
        parse_config = ProcessorConfig(
            output_dir=str(Path(os.getenv('NOVA_PHASE_MARKDOWN_PARSE'))),
            components=components
        )
        consolidate_config = ProcessorConfig(
            output_dir=str(Path(os.getenv('NOVA_PHASE_MARKDOWN_CONSOLIDATE'))),
            components=components
        )
        aggregate_config = ProcessorConfig(
            output_dir=str(Path(os.getenv('NOVA_PHASE_MARKDOWN_AGGREGATE'))),
            components=components
        )
        split_config = ProcessorConfig(
            output_dir=str(Path(os.getenv('NOVA_PHASE_MARKDOWN_SPLIT'))),
            components=components
        )
        
        # Register processors
        pipeline.register_processor('MARKDOWN_PARSE', MarkdownProcessor(parse_config, config))
        pipeline.register_processor('MARKDOWN_CONSOLIDATE', MarkdownConsolidateProcessor(consolidate_config, config))
        pipeline.register_processor('MARKDOWN_AGGREGATE', MarkdownAggregateProcessor(aggregate_config, config))
        pipeline.register_processor('MARKDOWN_SPLIT_THREEFILES', ThreeFileSplitProcessor(split_config, config))
        
        # Run pipeline
        success = await pipeline.run()
        if not success:
            logger.error("Pipeline failed")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Failed to process documents: {str(e)}")
        return False 