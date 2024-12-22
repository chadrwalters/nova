"""Command line interface for Nova document processor."""

import os
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple
import argparse

from ..core import logging as nova_logging
from ..core.paths import NovaPaths
from ..core.pipeline import Pipeline
from ..core.config import NovaConfig, PathsConfig, MarkdownConfig, ImageConfig, OfficeConfig
from ..core.errors import NovaError
from ..core.logging import info, error, success, warning

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

def setup_environment(args: argparse.Namespace) -> Tuple[NovaPaths, None]:
    """Setup environment for processing.
    
    Args:
        args: Command line arguments
        
    Returns:
        Tuple of paths and None (logger no longer needed in return)
    """
    # Setup logging
    nova_logging.setup_logger(
        log_file=Path(os.path.expanduser('~/nova.log')),
        level=args.log_level
    )
    
    # Load paths from environment
    try:
        paths = NovaPaths.from_env()
    except Exception as e:
        error(f"Failed to load paths from environment: {e}")
        sys.exit(1)
    
    return paths, None

def main() -> int:
    """Main entry point."""
    # Parse arguments
    args = parse_args()
    
    # Setup environment
    paths, _ = setup_environment(args)
    
    # Create pipeline configuration
    try:
        # Create full config using environment
        config = NovaConfig.from_env(paths)
        
        # Create and run pipeline
        pipeline = Pipeline(config)
        
        if args.dry_run:
            info("Dry run mode - showing what would be processed:")
            # Add dry run logic here
            return 0
            
        if args.show_state:
            info("Current processing state:")
            # Add state display logic here
            return 0
            
        if args.scan:
            info("Directory structure:")
            # Add directory scan logic here
            return 0
            
        if args.reset:
            warning("Resetting processing state...")
            # Add reset logic here
            return 0
        
        # Check if input directory exists
        input_dir = Path(config.paths.input_dir)
        if not input_dir.exists():
            error(f"Input directory does not exist: {input_dir}")
            return 1
        
        pipeline.process()
        success("Processing completed successfully")
        return 0
        
    except NovaError as e:
        error(str(e))
        return 1
        
    except Exception as e:
        error(f"Unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 