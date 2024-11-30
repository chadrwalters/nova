#!/usr/bin/env python3

import os
import sys
import logging
import hashlib
from pathlib import Path
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

import click
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from pypdf import PdfReader

from colors import Colors, console
from ..core.exceptions import PDFConversionError

# Logging Configuration
logging.basicConfig(
    filename='pdf_converter.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class PDFConverter:
    """Handles conversion of PDF files to Markdown format."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize PDFConverter with optional caching.
        
        Args:
            cache_dir: Directory to store cached conversions
        """
        self.cache_dir = cache_dir
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    @lru_cache(maxsize=32)
    def _get_page_content(page) -> str:
        """Cache and extract text from a single page."""
        return page.extract_text() or ""

    def _get_cache_path(self, pdf_path: Path) -> Optional[Path]:
        """Generate cache file path based on PDF content hash."""
        if not self.cache_dir:
            return None
            
        try:
            # Use first 1MB of file for hash calculation
            with open(pdf_path, 'rb') as f:
                content = f.read(1024 * 1024)
                file_hash = hashlib.md5(content).hexdigest()
            return self.cache_dir / f"{file_hash}.md"
        except Exception as e:
            logging.warning(f"Cache generation failed: {e}")
            return None

    def _process_page(self, page, page_num: int) -> tuple[int, str]:
        """Process a single page and return its content with page number."""
        try:
            content = self._get_page_content(page)
            return page_num, content
        except Exception as e:
            logging.error(f"Error processing page {page_num}: {e}")
            return page_num, ""

    def convert_pdf_to_markdown(
        self,
        pdf_path: Path,
        output_path: Optional[Path] = None,
        max_workers: int = 4
    ) -> str:
        """
        Convert a PDF file to Markdown format using parallel processing.

        Args:
            pdf_path: Path to the PDF file
            output_path: Optional path to save the markdown output
            max_workers: Maximum number of parallel workers

        Returns:
            str: Converted markdown content

        Raises:
            PDFConversionError: If conversion fails
        """
        try:
            # Check cache first
            cache_path = self._get_cache_path(pdf_path)
            if cache_path and cache_path.exists():
                content = cache_path.read_text(encoding='utf-8')
                if output_path:
                    output_path.write_text(content, encoding='utf-8')
                return content

            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            page_contents: List[str] = [""] * total_pages

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console
            ) as progress:
                task = progress.add_task(
                    f"Converting PDF: {pdf_path.name}",
                    total=total_pages
                )

                # Process pages in parallel
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_page = {
                        executor.submit(self._process_page, page, i): i
                        for i, page in enumerate(reader.pages)
                    }

                    for future in as_completed(future_to_page):
                        page_num, content = future.result()
                        page_contents[page_num] = content
                        progress.update(task, advance=1)

            # Join all pages with double newlines
            final_content = "\n\n".join(content for content in page_contents if content)

            # Save to cache if enabled
            if cache_path:
                cache_path.write_text(final_content, encoding='utf-8')

            # Save to output if specified
            if output_path:
                output_path.write_text(final_content, encoding='utf-8')

            return final_content

        except Exception as e:
            raise PDFConversionError(f"Failed to convert PDF {pdf_path}: {str(e)}") from e

@click.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path(), required=False)
@click.option('--cache-dir', type=click.Path(), help='Directory to store cached conversions')
@click.option('--workers', type=int, default=4, help='Number of parallel workers')
@click.option('--verbose', is_flag=True, help='Increase output verbosity')
def main(
    input_file: str,
    output_file: Optional[str],
    cache_dir: Optional[str],
    workers: int,
    verbose: bool
):
    """Convert PDF to Markdown with embedded images."""
    try:
        input_path = Path(input_file)
        output_path = Path(output_file) if output_file else input_path.with_suffix('.md')
        cache_path = Path(cache_dir) if cache_dir else None

        converter = PDFConverter(cache_dir=cache_path)
        try:
            converter.convert_pdf_to_markdown(
                pdf_path=input_path,
                output_path=output_path,
                max_workers=workers
            )
            Colors.success(f"Successfully converted {input_path.name}")
            success = True
        except PDFConversionError as e:
            Colors.error(f"Conversion failed: {str(e)}")
            success = False

        sys.exit(0 if success else 1)

    except Exception as e:
        Colors.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 