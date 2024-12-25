"""Main entry point for Nova document processor."""

import asyncio
import os
from pathlib import Path
from typing import Dict, Any, Optional

from .core.config import load_config, ProcessorConfig, ComponentConfig, PathConfig, PipelineConfig
from .core.logging import get_logger
from .core.errors import PipelineError
from .core import PipelineManager
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
        # Create pipeline configuration
        paths = PathConfig(base_dir=str(Path(os.getenv('NOVA_BASE_DIR'))))
        
        # Create processor configurations
        parse_config = ProcessorConfig(
            name="MARKDOWN_PARSE",
            description="Parse and process markdown files with embedded content",
            processor="MarkdownProcessor",
            output_dir=str(Path(os.getenv('NOVA_PHASE_MARKDOWN_PARSE'))),
            enabled=True
        )
        
        consolidate_config = ProcessorConfig(
            name="MARKDOWN_CONSOLIDATE",
            description="Consolidate markdown files with their attachments",
            processor="MarkdownConsolidateProcessor",
            output_dir=str(Path(os.getenv('NOVA_PHASE_MARKDOWN_CONSOLIDATE'))),
            enabled=True
        )
        
        aggregate_config = ProcessorConfig(
            name="MARKDOWN_AGGREGATE",
            description="Aggregate all consolidated markdown files into a single file",
            processor="MarkdownAggregateProcessor",
            output_dir=str(Path(os.getenv('NOVA_PHASE_MARKDOWN_AGGREGATE'))),
            enabled=True
        )
        
        split_config = ProcessorConfig(
            name="MARKDOWN_SPLIT_THREEFILES",
            description="Split aggregated markdown into summary, raw notes, and attachments",
            processor="ThreeFileSplitProcessor",
            output_dir=str(Path(os.getenv('NOVA_PHASE_MARKDOWN_SPLIT'))),
            enabled=True
        )
        
        # Create pipeline configuration
        config = PipelineConfig(
            paths=paths,
            phases=[parse_config, consolidate_config, aggregate_config, split_config],
            input_dir=input_dir,
            output_dir=output_dir
        )
        
        # Set up pipeline manager
        pipeline = PipelineManager(config)
        
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