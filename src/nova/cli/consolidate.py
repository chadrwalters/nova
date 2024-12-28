"""Consolidate command line interface."""

import os
import sys
import logging
import asyncio
from pathlib import Path

import yaml

from nova.core.config.base import PipelineConfig, CacheConfig
from nova.core.pipeline.pipeline_manager import PipelineManager
from nova.core.errors import ValidationError


async def main():
    """Main entry point."""
    try:
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        # Load configuration
        config_path = os.environ.get('NOVA_CONFIG_PATH', 'config/pipeline_config.yaml')
        logger.info(f"Loading configuration from {config_path}")

        with open(config_path) as f:
            config_data = yaml.safe_load(f)

        # Extract pipeline configuration
        if 'pipeline' in config_data:
            pipeline_data = config_data['pipeline']
        else:
            pipeline_data = config_data

        # Create cache configuration if present
        if 'cache' in pipeline_data:
            cache_config = CacheConfig(**pipeline_data['cache'])
            pipeline_data['cache'] = cache_config

        # Create pipeline configuration
        config = PipelineConfig(**pipeline_data)

        # Run pipeline
        logger.info("Running consolidation pipeline...")
        pipeline = PipelineManager(config)
        await pipeline.run()

    except ValidationError as e:
        logger.error(f"Pipeline failed: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)
    finally:
        if 'pipeline' in locals():
            await pipeline.cleanup()


if __name__ == '__main__':
    asyncio.run(main()) 