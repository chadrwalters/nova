"""Command for consolidating markdown files."""

import click
from pathlib import Path
import os
import asyncio
from typing import Optional

from ...core.logging import get_logger
from ...core.config import load_config
from ...core.errors import ConfigurationError
from ...main import process_files, display_summary

logger = get_logger(__name__)

@click.command()
@click.option('--input-dir', '-i', help='Input directory')
@click.option('--output-dir', '-o', help='Output directory')
@click.option('--analyze-images', '-a', is_flag=True, help='Analyze images with OpenAI Vision API')
def consolidate(input_dir: Optional[str], output_dir: Optional[str], analyze_images: bool):
    """Consolidate markdown files and their attachments."""
    try:
        # Get directories from environment if not provided
        input_dir = input_dir or os.path.expandvars(os.environ.get('NOVA_INPUT_DIR', ''))
        output_dir = output_dir or os.path.expandvars(os.environ.get('NOVA_OUTPUT_DIR', ''))
        
        if not input_dir or not output_dir:
            raise ConfigurationError("Input and output directories must be specified")
        
        # Convert to Path objects
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        # Verify directories exist
        if not input_path.exists():
            raise ConfigurationError(f"Input directory does not exist: {input_path}")
        
        # Create output directory if it doesn't exist
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Run processing
        stats = asyncio.run(process_files(input_path, output_path, analyze_images))
        
        # Display summary
        display_summary(stats, input_path)
        
    except Exception as e:
        logger.error(f"Consolidation failed: {str(e)}")
        raise 