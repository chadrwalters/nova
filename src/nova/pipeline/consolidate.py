"""Consolidation pipeline implementation."""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from rich.console import Console
from rich.table import Table

from ..core.config import load_config, ProcessorConfig
from ..core.utils.progress import ProgressTracker, ProcessingStatus
from ..phases.parse import MarkdownProcessor
from ..phases.consolidate import MarkdownConsolidateProcessor
from ..phases.aggregate import MarkdownAggregateProcessor
from ..phases.split import ThreeFileSplitProcessor
from ..core.logging import setup_logging

logger = logging.getLogger(__name__)
setup_logging(level=os.getenv('NOVA_LOG_LEVEL', 'DEBUG'))
console = Console()

async def run_pipeline() -> bool:
    """Run the consolidation pipeline.
    
    Returns:
        True if pipeline completed successfully, False otherwise
    """
    try:
        # Load pipeline configuration
        pipeline_config = load_config()
        
        # Initialize processors
        parse_processor = MarkdownProcessor(
            ProcessorConfig(
                name='MARKDOWN_PARSE',
                description='Parse and process markdown files with embedded content',
                output_dir=os.environ.get('NOVA_PHASE_MARKDOWN_PARSE'),
                processor='MarkdownProcessor'
            ),
            pipeline_config
        )
        
        consolidate_processor = MarkdownConsolidateProcessor(
            ProcessorConfig(
                name='MARKDOWN_CONSOLIDATE',
                description='Consolidate markdown files with their attachments',
                output_dir=os.environ.get('NOVA_PHASE_MARKDOWN_CONSOLIDATE'),
                processor='MarkdownConsolidateProcessor'
            ),
            pipeline_config
        )
        
        aggregate_processor = MarkdownAggregateProcessor(
            ProcessorConfig(
                name='MARKDOWN_AGGREGATE',
                description='Aggregate all consolidated markdown files into a single file',
                output_dir=os.environ.get('NOVA_PHASE_MARKDOWN_AGGREGATE'),
                processor='MarkdownAggregateProcessor'
            ),
            pipeline_config
        )
        
        split_processor = ThreeFileSplitProcessor(
            ProcessorConfig(
                name='MARKDOWN_SPLIT',
                description='Split aggregated markdown into separate files for summary, raw notes, and attachments',
                output_dir=os.environ.get('NOVA_PHASE_MARKDOWN_SPLIT'),
                processor='ThreeFileSplitProcessor'
            ),
            pipeline_config
        )
        
        # Count input files
        input_dir = Path(os.environ.get('NOVA_INPUT_DIR'))
        markdown_files = list(input_dir.rglob('*.md'))
        total_files = len(markdown_files)
        
        # Initialize progress trackers
        parse_processor.progress_tracker.start_task(
            'MARKDOWN_PARSE',
            'Parse markdown files',
            total_files
        )
        consolidate_processor.progress_tracker.start_task(
            'MARKDOWN_CONSOLIDATE',
            'Consolidate markdown files',
            total_files
        )
        aggregate_processor.progress_tracker.start_task(
            'MARKDOWN_AGGREGATE',
            'Aggregate markdown files',
            total_files
        )
        split_processor.progress_tracker.start_task(
            'MARKDOWN_SPLIT',
            'Split markdown files',
            total_files
        )
        
        # Run pipeline phases
        parse_result = await parse_processor.process()
        if not parse_result.success:
            logger.error(f"Parse phase failed: {parse_result.errors}")
            return False
        
        logger.info(f"Successfully parsed {len(parse_result.processed_files)} files")
        
        consolidate_result = await consolidate_processor.process()
        if not consolidate_result.success:
            logger.error(f"Consolidate phase failed: {consolidate_result.errors}")
            return False
            
        logger.info(f"Successfully consolidated {len(consolidate_result.processed_files)} files")
        
        aggregate_result = await aggregate_processor.process()
        if not aggregate_result.success:
            logger.error(f"Aggregate phase failed: {aggregate_result.errors}")
            return False
            
        logger.info(f"Successfully aggregated {len(aggregate_result.processed_files)} files")
        
        split_result = await split_processor.process()
        if not split_result.success:
            logger.error(f"Split phase failed: {split_result.errors}")
            return False
            
        logger.info(f"Successfully split {len(split_result.processed_files)} files")
        
        return True
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        return False

def main():
    """Main entry point."""
    try:
        import asyncio
        asyncio.run(run_pipeline())
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        return 1
    return 0

if __name__ == '__main__':
    exit(main()) 