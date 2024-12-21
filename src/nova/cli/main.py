"""Command line interface for Nova document processor."""

import os
import sys
import logging as py_logging
import argparse
from pathlib import Path
from typing import Dict, Optional, Tuple

from ..core import logging as nova_logging
from ..core.paths import NovaPaths
from ..core.pipeline import Pipeline
from ..core.config import NovaConfig, PathsConfig, MarkdownConfig, ImageConfig, OfficeConfig
from ..core.errors import NovaError

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Nova Document Processor"
    )
    
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force processing of all files"
    )
    
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be done without making changes"
    )
    
    parser.add_argument(
        "--show-state", "-s",
        action="store_true",
        help="Display current processing state"
    )
    
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Show directory structure"
    )
    
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset processing state"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=os.environ.get("NOVA_LOG_LEVEL", "INFO"),
        help="Set logging level"
    )
    
    return parser.parse_args()

def setup_environment(args: argparse.Namespace) -> Tuple[NovaPaths, py_logging.Logger]:
    """Setup environment for processing.
    
    Args:
        args: Command line arguments
        
    Returns:
        Tuple of paths and logger
    """
    # Setup logging
    logger = nova_logging.get_logger(__name__)
    nova_logging.setup_logger(
        log_file=Path(os.path.expanduser('~/nova.log')),
        level=args.log_level
    )
    
    # Load paths from environment
    try:
        paths = NovaPaths.from_env()
    except Exception as e:
        logger.error(f"Failed to load paths from environment: {e}")
        sys.exit(1)
    
    return paths, logger

def main() -> int:
    """Main entry point."""
    # Parse arguments
    args = parse_args()
    
    # Setup environment
    paths, logger = setup_environment(args)
    
    # Create pipeline configuration
    try:
        # Create full config using environment
        config = NovaConfig.from_env(paths)
        
        # Create and run pipeline
        pipeline = Pipeline(config)
        pipeline.process()
        return 0
        
    except NovaError as e:
        logger.error(str(e))
        return 1
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 