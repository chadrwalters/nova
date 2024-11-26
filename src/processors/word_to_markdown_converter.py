#!/usr/bin/env python3

import os
import sys
import logging
from pathlib import Path
from typing import Optional
import mammoth
import docx
from rich.progress import Progress, SpinnerColumn, TextColumn

from colors import Colors, console

class WordConverter:
    def __init__(self, input_path: Path, output_path: Path, media_dir: Optional[Path] = None, verbose: bool = False):
        self.input_path = input_path
        self.output_path = output_path
        self.media_dir = media_dir or output_path.parent / '_media'
        self.verbose = verbose
        self.logger = self.setup_logging()
        
    def setup_logging(self) -> logging.Logger:
        logger = logging.getLogger(__name__)
        if self.verbose:
            logger.setLevel(logging.DEBUG)
        return logger

    def convert(self) -> bool:
        """Convert Word document to Markdown."""
        try:
            Colors.info(f"Converting Word document: {self.input_path}")
            
            # Ensure media directory exists
            self.media_dir.mkdir(parents=True, exist_ok=True)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Converting Word document...", total=1)
                
                # Configure image handling
                image_handler = mammoth.images.inline(lambda image: {
                    "src": self._save_image(image)
                })
                
                # Convert document
                with open(self.input_path, "rb") as docx_file:
                    result = mammoth.convert_to_markdown(
                        docx_file,
                        convert_image=image_handler
                    )
                
                # Write markdown content
                self.output_path.write_text(result.value, encoding='utf-8')
                
                # Log any warnings
                for warning in result.messages:
                    self.logger.warning(warning)
                
                progress.update(task, advance=1)
                
                Colors.success(f"Conversion complete: {self.output_path}")
                self.logger.info(f"Successfully converted {self.input_path} to {self.output_path}")
                return True
                
        except Exception as e:
            Colors.error(f"Conversion failed: {e}")
            self.logger.error(f"Conversion failed: {e}")
            return False

    def _save_image(self, image):
        """Save embedded image and return its relative path."""
        try:
            image_filename = f"image_{hash(image.bytes)}_{image.content_type.split('/')[-1]}"
            image_path = self.media_dir / image_filename
            
            with open(image_path, 'wb') as f:
                f.write(image.bytes)
            
            return f"_media/{image_filename}"
        except Exception as e:
            self.logger.error(f"Failed to save image: {e}")
            return ""

if __name__ == '__main__':
    import click

    @click.command()
    @click.argument('input_file', type=click.Path(exists=True))
    @click.argument('output_file', type=click.Path(), required=False)
    @click.option('--media-dir', type=click.Path(), help='Directory to store media files')
    @click.option('--verbose', is_flag=True, help='Increase output verbosity')
    def main(input_file: str, output_file: Optional[str], media_dir: Optional[str], verbose: bool):
        """Convert Word document to Markdown with embedded images."""
        try:
            input_path = Path(input_file)
            output_path = Path(output_file) if output_file else input_path.with_suffix('.md')
            media_dir_path = Path(media_dir) if media_dir else output_path.parent / '_media'
            
            converter = WordConverter(input_path, output_path, media_dir_path, verbose)
            success = converter.convert()
            
            sys.exit(0 if success else 1)
            
        except Exception as e:
            Colors.error(f"Error: {str(e)}")
            sys.exit(1)

    main() 