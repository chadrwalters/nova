#!/usr/bin/env python3

import os
import sys
import logging
from pathlib import Path
from typing import Optional
import shutil

import click
from marker.convert import convert_single_pdf as marker_convert_pdf
from marker.models import load_all_models
from rich.progress import Progress, SpinnerColumn, TextColumn

from colors import Colors, console

# Logging Configuration
logging.basicConfig(
    filename='pdf_converter.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def process_single_pdf(input_path: Path, output_path: Path, media_dir: Path) -> bool:
    """Convert a single PDF file to markdown."""
    try:
        # Verify input is a file, not a directory
        if not input_path.is_file():
            Colors.warning(f"Skipping directory with .pdf extension: {input_path}")
            return False
            
        Colors.info(f"Converting PDF: {input_path}")
        
        # Ensure media directory exists
        media_dir.mkdir(parents=True, exist_ok=True)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # Load models
            task = progress.add_task("Loading models...", total=1)
            model_lst = load_all_models()
            progress.update(task, advance=1)
            
            # Convert PDF
            task = progress.add_task("Converting PDF...", total=1)
            markdown_text, images, metadata = marker_convert_pdf(
                str(input_path),
                model_lst
            )
            
            # Process output
            output_path.write_text(markdown_text, encoding='utf-8')
            progress.update(task, advance=1)
            
            return True
            
    except Exception as e:
        Colors.error(f"Conversion failed: {e}")
        return False

class PDFConverter:
    def __init__(self, input_path: Path, output_path: Path, media_dir: Optional[Path] = None, verbose: bool = False):
        self.input_path = Path(input_path)  # Ensure Path object
        self.output_path = Path(output_path)
        self.media_dir = Path(media_dir) if media_dir else output_path.parent / '_media'
        self.verbose = verbose
        self.logger = self.setup_logging()
        
    def setup_logging(self) -> logging.Logger:
        """Configure logging based on verbosity level."""
        logger = logging.getLogger(__name__)
        if self.verbose:
            logger.setLevel(logging.DEBUG)
        return logger

    def convert(self) -> bool:
        """Convert PDF to Markdown using Marker."""
        try:
            # Verify input is a file
            if not self.input_path.is_file():
                raise ValueError(f"Not a file: {self.input_path}")
                
            return process_single_pdf(self.input_path, self.output_path, self.media_dir)
                
        except Exception as e:
            Colors.error(f"Conversion failed: {e}")
            self.logger.error(f"Conversion failed: {e}")
            return False

@click.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path(), required=False)
@click.option('--media-dir', type=click.Path(), help='Directory to store media files')
@click.option('--verbose', is_flag=True, help='Increase output verbosity')
def main(input_file: str, output_file: Optional[str], media_dir: Optional[str], verbose: bool):
    """Convert PDF to Markdown with embedded images."""
    try:
        input_path = Path(input_file)
        output_path = Path(output_file) if output_file else input_path.with_suffix('.md')
        media_dir_path = Path(media_dir) if media_dir else output_path.parent / '_media'
        
        converter = PDFConverter(input_path, output_path, media_dir_path, verbose)
        success = converter.convert()
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        Colors.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 