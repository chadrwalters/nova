#!/usr/bin/env python3

import os
import sys
from pathlib import Path
from typing import List, Optional
import typer
from datetime import datetime

from colors import NovaConsole
from src.utils.timing import timed_section

app = typer.Typer(help="Nova Markdown Consolidator")
nova_console = NovaConsole()

def process_input(input_path: Path, recursive: bool = False) -> List[Path]:
    """Process input path and return list of markdown files."""
    files = []
    if input_path.is_dir():
        pattern = "**/*.md" if recursive else "*.md"
        files.extend(input_path.glob(pattern))
    elif input_path.is_file() and input_path.suffix.lower() == '.md':
        files.append(input_path)
    return sorted(files)

def process_file(file_path: Path) -> str:
    """Process a single markdown file."""
    try:
        return file_path.read_text(encoding='utf-8')
    except Exception as e:
        nova_console.error(f"Failed to read file", str(e))
        raise typer.Exit(1)

@app.command()
def consolidate(
    input_path: Path = typer.Argument(..., help="Input markdown files path"),
    output_file: Path = typer.Argument(..., help="Output consolidated file path"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Process directories recursively"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Increase output verbosity")
) -> None:
    """Consolidate multiple markdown files into a single document."""
    try:
        # Find markdown files
        nova_console.process_start("markdown consolidation", str(input_path))
        files = process_input(input_path, recursive)
        
        if not files:
            nova_console.error("No markdown files found")
            raise typer.Exit(1)
        
        # Process files
        contents = []
        for file in files:
            if verbose:
                nova_console.process_item(str(file))
            contents.append(process_file(file))
        
        # Write output
        output_file.parent.mkdir(parents=True, exist_ok=True)
        combined = "\n\n---\n\n".join(contents)
        output_file.write_text(combined, encoding='utf-8')
        
        # Show completion stats
        size_mb = output_file.stat().st_size / (1024 * 1024)
        nova_console.process_complete("markdown consolidation", {
            "Files": f"{len(files)} processed",
            "Output": str(output_file),
            "Size": f"{size_mb:.1f}MB"
        })
        
    except Exception as e:
        nova_console.error("Markdown consolidation failed", str(e))
        raise typer.Exit(1)

if __name__ == "__main__":
    app()