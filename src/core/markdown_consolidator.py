#!/usr/bin/env python3

import os
import sys
from pathlib import Path
from typing import List, Optional, Dict
import typer
from datetime import datetime
import re
import base64
from dataclasses import dataclass
import hashlib
import shutil

from src.utils.colors import NovaConsole
from src.utils.timing import timed_section

app = typer.Typer(help="Nova Markdown Consolidator")
nova_console = NovaConsole()

@dataclass
class MarkdownFile:
    path: Path
    date: datetime
    content: str
    media_files: List[Path]

def extract_date_from_filename(filename: str) -> datetime:
    """Extract date from filename in format YYYYMMDD."""
    match = re.match(r'(\d{8})', filename)
    if match:
        date_str = match.group(1)
        try:
            return datetime.strptime(date_str, '%Y%m%d')
        except ValueError:
            pass
    return datetime.fromtimestamp(0)  # Default to epoch if no date found

def process_image_links(content: str, file_path: Path, media_dir: Path) -> tuple[str, List[Path]]:
    """Process and extract image links from markdown content."""
    media_files = []
    
    # Handle base64 encoded images
    def replace_base64_image(match):
        alt_text = match.group(1)
        image_type = match.group(2)
        base64_data = match.group(3)
        
        try:
            # Generate unique filename based on content hash
            content_hash = hashlib.md5(base64_data.encode()).hexdigest()[:12]
            image_filename = f"image_{content_hash}.{image_type}"
            image_path = media_dir / image_filename
            
            # Save image if it doesn't exist
            if not image_path.exists():
                image_data = base64.b64decode(base64_data)
                image_path.write_bytes(image_data)
            
            media_files.append(image_path)
            return f"![{alt_text}](_media/{image_filename})"
            
        except Exception as e:
            nova_console.error(f"Failed to process base64 image", str(e))
            return f"![{alt_text}](error_processing_image)"
    
    # Handle base64 encoded images
    content = re.sub(
        r'!\[([^\]]*)\]\(data:image/([^;]+);base64,([^\)]+)\)',
        replace_base64_image,
        content
    )
    
    # Handle local image references
    def replace_local_image(match):
        alt_text = match.group(1)
        image_path = match.group(2)
        
        # Convert to Path object relative to the markdown file
        full_image_path = (file_path.parent / image_path).resolve()
        if full_image_path.exists():
            # Generate unique filename
            image_filename = f"image_{hashlib.md5(str(full_image_path).encode()).hexdigest()[:12]}{full_image_path.suffix}"
            new_image_path = media_dir / image_filename
            
            # Copy image if it doesn't exist
            if not new_image_path.exists():
                shutil.copy2(full_image_path, new_image_path)
            
            media_files.append(new_image_path)
            return f"![{alt_text}](_media/{image_filename})"
        return match.group(0)  # Keep original if image not found
    
    # Handle local images
    content = re.sub(
        r'!\[([^\]]*)\]\(([^:\)]+)\)',
        replace_local_image,
        content
    )
    
    return content, media_files

def process_file(file_path: Path, media_dir: Path) -> MarkdownFile:
    """Process a single markdown file."""
    try:
        content = file_path.read_text(encoding='utf-8')
        
        # Clean content
        content = content.replace('\u2028', '\n').replace('\u2029', '\n')  # Line separators
        content = content.replace('\r\n', '\n').replace('\r', '\n')  # Normalize line endings
        content = re.sub(r'[\u200B-\u200D\uFEFF]', '', content)  # Remove zero-width spaces
        
        # Process images and get media files
        content, media_files = process_image_links(content, file_path, media_dir)
        
        # Add file header
        header = f"# {file_path.stem}\n\n"
        content = header + content
        
        return MarkdownFile(
            path=file_path,
            date=extract_date_from_filename(file_path.stem),
            content=content,
            media_files=media_files
        )
    except Exception as e:
        nova_console.error(f"Failed to process file {file_path}", str(e))
        raise typer.Exit(1)

def process_input(input_path: Path, recursive: bool = False) -> List[Path]:
    """Process input path and return list of markdown files."""
    files = []
    if input_path.is_dir():
        pattern = "**/*.md" if recursive else "*.md"
        files.extend(input_path.glob(pattern))
    elif input_path.is_file() and input_path.suffix.lower() == '.md':
        files.append(input_path)
    return sorted(files)

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
        
        # Create media directory
        media_dir = output_file.parent / "_media"
        media_dir.mkdir(parents=True, exist_ok=True)
        
        # Process files
        processed_files: List[MarkdownFile] = []
        for file in files:
            if verbose:
                nova_console.process_item(str(file))
            processed_files.append(process_file(file, media_dir))
        
        # Sort files by date
        processed_files.sort(key=lambda x: x.date)
        
        # Write output
        output_file.parent.mkdir(parents=True, exist_ok=True)
        contents = []
        for pf in processed_files:
            contents.append(pf.content)
        
        combined = "\n\n---\n\n".join(contents)
        output_file.write_text(combined, encoding='utf-8')
        
        # Show completion stats
        size_mb = output_file.stat().st_size / (1024 * 1024)
        media_count = sum(len(pf.media_files) for pf in processed_files)
        nova_console.process_complete("markdown consolidation", {
            "Files": f"{len(files)} processed",
            "Media": f"{media_count} files",
            "Output": str(output_file),
            "Size": f"{size_mb:.1f}MB"
        })
        
    except Exception as e:
        nova_console.error("Markdown consolidation failed", str(e))
        raise typer.Exit(1)

if __name__ == "__main__":
    app()