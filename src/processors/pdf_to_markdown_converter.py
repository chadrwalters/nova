#!/usr/bin/env python3

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import typer

from pypdf import PdfReader
from colors import NovaConsole
from ..core.exceptions import PDFConversionError

# Initialize console
nova_console = NovaConsole()

class PDFConverter:
    def __init__(self, media_dir: Optional[Path] = None):
        """Initialize PDF converter."""
        self.media_dir = media_dir
        
    @staticmethod
    @lru_cache(maxsize=32)
    def _get_page_content(page) -> str:
        """Cache and extract text from a single page."""
        return page.extract_text() or ""

    def _process_page(self, page_info: tuple[int, Any]) -> tuple[int, str]:
        """Process a single page and return its content."""
        page_num, page = page_info
        try:
            content = self._get_page_content(page)
            if self.verbose:
                nova_console.process_item(f"Page {page_num + 1}")
            return page_num, content
        except Exception as e:
            nova_console.error(f"Failed to process page {page_num + 1}", str(e))
            return page_num, ""

    def convert_pdf_to_markdown(
        self,
        pdf_path: Path,
        output_path: Path,
        max_workers: int = 4,
        verbose: bool = False
    ) -> bool:
        """Convert PDF to Markdown format."""
        try:
            self.verbose = verbose
            nova_console.process_start("PDF to markdown conversion", str(pdf_path))

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Read PDF
            with open(pdf_path, 'rb') as file:
                reader = PdfReader(file)
                total_pages = len(reader.pages)

                # Process pages in parallel
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Create page processing tasks
                    futures = {
                        executor.submit(self._process_page, (i, page)): i
                        for i, page in enumerate(reader.pages)
                    }

                    # Collect results
                    page_contents = [""] * total_pages
                    for future in as_completed(futures):
                        page_num, content = future.result()
                        page_contents[page_num] = content

            # Join content and write output
            content = "\n\n".join(content for content in page_contents if content)
            output_path.write_text(content, encoding='utf-8')

            # Show completion stats
            size_mb = output_path.stat().st_size / (1024 * 1024)
            nova_console.process_complete("PDF conversion", {
                "Pages": f"{total_pages} processed",
                "Output": str(output_path),
                "Size": f"{size_mb:.1f}MB"
            })
            return True

        except Exception as e:
            nova_console.error("PDF conversion failed", str(e))
            return False

def main():
    """CLI entry point."""
    app = typer.Typer()

    @app.command()
    def convert(
        input_file: Path = typer.Argument(..., help="Input PDF file"),
        output_file: Path = typer.Argument(..., help="Output markdown file"),
        media_dir: Optional[Path] = typer.Option(None, help="Media output directory"),
        workers: int = typer.Option(4, help="Number of worker threads"),
        verbose: bool = typer.Option(False, help="Show detailed progress")
    ):
        """Convert PDF to Markdown with embedded images."""
        if not input_file.exists():
            nova_console.error("Input file not found", str(input_file))
            raise typer.Exit(1)

        converter = PDFConverter(media_dir=media_dir)
        success = converter.convert_pdf_to_markdown(
            input_file,
            output_file,
            max_workers=workers,
            verbose=verbose
        )
        raise typer.Exit(0 if success else 1)

    app()

if __name__ == '__main__':
    main() 