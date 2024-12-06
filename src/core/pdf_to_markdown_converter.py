#!/usr/bin/env python3

import os
import sys
from pathlib import Path
from typing import Optional
import typer
from pypdf import PdfReader
from datetime import datetime

from src.utils.colors import NovaConsole
from src.utils.timing import timed_section

app = typer.Typer(help="Nova PDF to Markdown Converter")
nova_console = NovaConsole()

@timed_section("Converting PDF")
def convert_pdf_to_markdown(pdf_path: Path, output_path: Path, media_dir: Optional[Path] = None) -> bool:
    """Convert PDF to markdown format."""
    try:
        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if media_dir:
            media_dir.mkdir(parents=True, exist_ok=True)

        # Start conversion
        nova_console.process_start("PDF conversion", str(pdf_path))
        
        # Read PDF
        reader = PdfReader(pdf_path)
        content = []
        
        # Extract text from each page
        for i, page in enumerate(reader.pages, 1):
            nova_console.process_item(f"Processing page {i}")
            text = page.extract_text()
            if text.strip():
                content.append(text)
        
        # Write markdown
        markdown_content = "\n\n".join(content)
        output_path.write_text(markdown_content, encoding='utf-8')
        
        # Show completion stats
        size_mb = output_path.stat().st_size / (1024 * 1024)
        nova_console.process_complete("PDF conversion", {
            "Pages": f"{len(reader.pages)} processed",
            "Output": str(output_path),
            "Size": f"{size_mb:.1f}MB"
        })
        
        return True
        
    except Exception as e:
        nova_console.error("PDF conversion failed", str(e))
        return False

@app.command()
def convert(
    input_file: Path = typer.Argument(..., help="Input PDF file path"),
    output_file: Path = typer.Argument(..., help="Output markdown file path"),
    media_dir: Optional[Path] = typer.Option(None, "--media-dir", help="Directory for extracted media")
) -> None:
    """Convert PDF file to markdown format."""
    if not convert_pdf_to_markdown(input_file, output_file, media_dir):
        raise typer.Exit(1)

if __name__ == "__main__":
    app()
