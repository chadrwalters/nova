"""Consolidate markdown files."""

from pathlib import Path
import asyncio
import sys
import logging
import os

from ..core.pipeline.manager import PipelineManager
from ..core.config import PipelineConfig


async def main() -> None:
    """Run the consolidation pipeline."""
    try:
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        
        # Load configuration
        logger.info("Loading configuration from config/pipeline_config.yaml")
        config = PipelineConfig.load("config/pipeline_config.yaml")
        
        # Create pipeline manager
        logger.info("Running consolidation pipeline...")
        pipeline = PipelineManager(config)
        
        # Get input files
        input_dir = os.environ.get('NOVA_INPUT_DIR')
        if not input_dir:
            logger.error("NOVA_INPUT_DIR environment variable not set")
            sys.exit(1)
            
        input_dir = Path(input_dir)
        if not input_dir.exists():
            logger.error(f"Input directory does not exist: {input_dir}")
            sys.exit(1)
            
        input_files = list(input_dir.glob('**/*.md'))
        
        if not input_files:
            logger.warning("No markdown files found in input directory")
            sys.exit(0)
            
        # Run pipeline
        async with pipeline:
            success = await pipeline.run()
            
            if not success:
                logger.error("Pipeline failed")
                sys.exit(1)
                
            logger.info("Pipeline completed successfully")
            
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        sys.exit(1)
        
    finally:
        await pipeline.cleanup()


if __name__ == '__main__':
    asyncio.run(main()) 