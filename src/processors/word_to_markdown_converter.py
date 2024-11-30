#!/usr/bin/env python3

import os
import sys
import logging
from pathlib import Path
from typing import Optional
import mammoth
import docx
from rich.progress import Progress, SpinnerColumn, TextColumn

from colors import NovaConsole

class WordConverter:
    def __init__(self, input_file: Path, output_file: Path, media_dir: Optional[Path] = None, verbose: bool = False):
        self.input_file = input_file
        self.output_file = output_file
        self.media_dir = media_dir
        self.verbose = verbose
        self.console = NovaConsole()
        
    def convert(self) -> bool:
        """Convert Word document to Markdown."""
        try:
            if self.verbose:
                self.console.info(f"Converting {self.input_file.name}")

            # Create media directory if needed
            if self.media_dir:
                self.media_dir.mkdir(parents=True, exist_ok=True)
                if self.verbose:
                    self.console.info(f"Media directory: {self.media_dir}")

            # Convert document
            with open(self.input_file, 'rb') as docx_file:
                result = mammoth.convert_to_markdown(docx_file)
                markdown = result.value
                messages = result.messages

            # Log any warnings
            if messages and self.verbose:
                for message in messages:
                    self.console.warning(str(message))

            # Write output
            self.output_file.write_text(markdown, encoding='utf-8')
            if self.verbose:
                self.console.success(f"Created {self.output_file.name}")

            return True

        except Exception as e:
            self.console.error(f"Failed to convert {self.input_file.name}: {str(e)}")
            return False

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
            print(f"Error: {str(e)}")
            sys.exit(1)

    main() 