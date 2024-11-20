#!/usr/bin/env python3

import os
import sys
import logging
from pathlib import Path
from typing import Optional
import shutil

import click
from marker.convert import convert_single_pdf
from marker.models import load_all_models
from rich.progress import Progress, SpinnerColumn, TextColumn

from colors import Colors, console

# Logging Configuration
logging.basicConfig(
    filename='pdf_converter.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class PDFConverter:
    def __init__(self, input_path: Path, output_path: Path, media_dir: Optional[Path] = None, verbose: bool = False):
        self.input_path = input_path
        self.output_path = output_path
        self.media_dir = media_dir or output_path.parent / '_media'
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
            Colors.info(f"Converting PDF: {self.input_path}")
            
            # Ensure media directory exists
            self.media_dir.mkdir(parents=True, exist_ok=True)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                # Load models
                task = progress.add_task("Loading models...", total=1)
                
                # Set device configuration
                import torch
                if torch.backends.mps.is_available():
                    device = "mps"
                    Colors.info("Using Apple Metal GPU acceleration")
                else:
                    device = "cpu"
                    Colors.info("Using CPU for processing")
                
                # Load models without explicit device
                model_lst = load_all_models()
                progress.update(task, advance=1)
                
                # Convert PDF
                task = progress.add_task("Converting PDF...", total=1)
                
                # Convert PDF to markdown
                markdown_text, images, metadata = convert_single_pdf(
                    str(self.input_path),
                    model_lst
                )
                
                # Save any extracted images
                if images:
                    for i, img_data in enumerate(images):
                        if isinstance(img_data, str):
                            # If image data is a string (path), copy the file
                            src_path = Path(img_data)
                            if src_path.exists():
                                dst_path = self.media_dir / f"image_{i}{src_path.suffix}"
                                shutil.copy2(src_path, dst_path)
                        else:
                            # If image data is bytes, write directly
                            img_path = self.media_dir / f"image_{i}.png"
                            with open(img_path, 'wb') as f:
                                f.write(img_data)
                
                # Write markdown content
                self.output_path.write_text(markdown_text, encoding='utf-8')
                progress.update(task, advance=1)
                
                # Verify the output file exists
                if not self.output_path.exists():
                    raise RuntimeError("Output file was not created")
                
                Colors.success(f"Conversion complete: {self.output_path}")
                self.logger.info(f"Successfully converted {self.input_path} to {self.output_path}")
                return True
                
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