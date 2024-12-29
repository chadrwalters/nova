"""Nova command line interface."""
import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Optional

from nova.config.manager import ConfigManager
from nova.core.logging import NovaFormatter, create_progress_bar, print_summary
from nova.core.pipeline import NovaPipeline

logger = logging.getLogger("nova")


def configure_logging(debug: bool = False, no_color: bool = False) -> None:
    """Configure logging.
    
    Args:
        debug: Whether to enable debug logging.
        no_color: Whether to disable colored output.
    """
    # Create handler with custom formatter
    handler = logging.StreamHandler()
    handler.setFormatter(NovaFormatter())
    
    # Configure root logger
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Configure nova logger
    logger.setLevel(logging.DEBUG if debug else logging.INFO)


async def main(args: Optional[List[str]] = None) -> int:
    """Run Nova pipeline.
    
    Args:
        args: Command line arguments.
        
    Returns:
        Exit code.
    """
    # Parse arguments
    parser = argparse.ArgumentParser(description="Nova document processing pipeline")
    parser.add_argument(
        "--input-dir",
        type=Path,
        help="Input directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Configuration file",
    )
    parser.add_argument(
        "--phases",
        nargs="+",
        default=["parse", "split"],
        help="Processing phases to run",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )
    
    parsed_args = parser.parse_args(args)
    
    # Configure logging
    configure_logging(
        debug=parsed_args.debug,
        no_color=parsed_args.no_color,
    )
    
    try:
        # Load configuration
        config = ConfigManager(parsed_args.config)
        
        # Create pipeline
        pipeline = NovaPipeline(config=config)
        
        # Get input directory
        input_dir = parsed_args.input_dir or config.input_dir
        if not input_dir:
            logger.error("No input directory specified")
            return 1
        
        # Get output directory
        output_dir = parsed_args.output_dir or config.output_dir
        if not output_dir:
            logger.error("No output directory specified")
            return 1
        
        # Get phases from config or command line
        phases = parsed_args.phases
        if hasattr(config, "phases"):
            phases = config.phases
        
        # Process directory
        await pipeline.process_directory(input_dir, phases)
        
        return 0
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 