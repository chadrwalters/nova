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
from PIL import Image

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
            image_filename = f"{file_path.stem}_{content_hash}.{image_type}"
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
        
        try:
            source_image_path = None
            
            # Remove any _media/ prefix from the search
            clean_image_path = image_path.replace('_media/', '')
            image_name = Path(clean_image_path).name
            
            # Search paths in priority order
            search_paths = [
                # 1. Direct path relative to markdown file
                file_path.parent / clean_image_path,
                # 2. In markdown file's directory
                file_path.parent / image_name,
                # 3. In markdown file's associated directory
                file_path.parent / file_path.stem / image_name,
                # 4. In _media subdirectory of markdown file's associated directory
                file_path.parent / file_path.stem / "_media" / image_name,
                # 5. In root _media directory
                file_path.parent / "_media" / image_name,
                # 6. Try in the parent directory
                file_path.parent.parent / image_name,
                # 7. Try in Screenshots directory (common for macOS)
                file_path.parent / "Screenshots" / image_name,
                # 8. Try in the markdown file's directory with original path
                file_path.parent / file_path.stem / clean_image_path,
                # 9. Try in the markdown file's directory with original filename
                file_path.parent / file_path.stem / Path(clean_image_path).name,
                # 10. Try in the markdown file's _media directory with original filename
                file_path.parent / file_path.stem / "_media" / Path(clean_image_path).name,
                # 11. Try in the markdown file's directory with just the number prefix
                file_path.parent / re.sub(r'^(\d+).*$', r'\1_image_0.png', image_name),
                # 12. Try in the markdown file's directory with just the number and index
                file_path.parent / re.sub(r'^(\d+).*?(\d+).*$', r'\1_image_\2.png', image_name),
                # 13. Try in the markdown file's _media directory with just the number prefix
                file_path.parent / "_media" / re.sub(r'^(\d+).*$', r'\1_image_0.png', image_name),
                # 14. Try in the markdown file's _media directory with just the number and index
                file_path.parent / "_media" / re.sub(r'^(\d+).*?(\d+).*$', r'\1_image_\2.png', image_name),
                # 15. Try in the markdown file's directory with just the number
                file_path.parent / re.sub(r'^(\d+).*$', r'\1.png', image_name),
                # 16. Try in the markdown file's _media directory with just the number
                file_path.parent / "_media" / re.sub(r'^(\d+).*$', r'\1.png', image_name),
                # 17. Try in the markdown file's directory with just the number and extension
                file_path.parent / re.sub(r'^(\d+).*(\.[^.]+)$', r'\1\2', image_name),
                # 18. Try in the markdown file's _media directory with just the number and extension
                file_path.parent / "_media" / re.sub(r'^(\d+).*(\.[^.]+)$', r'\1\2', image_name),
                # 19. Try in the markdown file's directory with just the number and PNG extension
                file_path.parent / f"{re.sub(r'^(\d+).*$', r'\1', image_name)}.png",
                # 20. Try in the markdown file's _media directory with just the number and PNG extension
                file_path.parent / "_media" / f"{re.sub(r'^(\d+).*$', r'\1', image_name)}.png",
                # 21. Try in the markdown file's directory with just the number and HEIC extension
                file_path.parent / f"{re.sub(r'^(\d+).*$', r'\1', image_name)}.heic",
                # 22. Try in the markdown file's _media directory with just the number and HEIC extension
                file_path.parent / "_media" / f"{re.sub(r'^(\d+).*$', r'\1', image_name)}.heic",
                # 23. Try in the markdown file's directory with just the number and JPEG extension
                file_path.parent / f"{re.sub(r'^(\d+).*$', r'\1', image_name)}.jpeg",
                # 24. Try in the markdown file's _media directory with just the number and JPEG extension
                file_path.parent / "_media" / f"{re.sub(r'^(\d+).*$', r'\1', image_name)}.jpeg",
                # 25. Try in the markdown file's directory with just the number and JPG extension
                file_path.parent / f"{re.sub(r'^(\d+).*$', r'\1', image_name)}.jpg",
                # 26. Try in the markdown file's _media directory with just the number and JPG extension
                file_path.parent / "_media" / f"{re.sub(r'^(\d+).*$', r'\1', image_name)}.jpg",
                # 27. Try in the markdown file's directory with just the number and WEBP extension
                file_path.parent / f"{re.sub(r'^(\d+).*$', r'\1', image_name)}.webp",
                # 28. Try in the markdown file's _media directory with just the number and WEBP extension
                file_path.parent / "_media" / f"{re.sub(r'^(\d+).*$', r'\1', image_name)}.webp",
                # 29. Try in the markdown file's directory with just the number and SVG extension
                file_path.parent / f"{re.sub(r'^(\d+).*$', r'\1', image_name)}.svg",
                # 30. Try in the markdown file's _media directory with just the number and SVG extension
                file_path.parent / "_media" / f"{re.sub(r'^(\d+).*$', r'\1', image_name)}.svg"
            ]
            
            # Try each path until we find the image
            for path in search_paths:
                if path.exists():
                    source_image_path = path
                    nova_console.process_item(f"Found image at: {source_image_path}")
                    break
            
            if source_image_path and source_image_path.exists():
                # Create a filename that preserves the original name and extension
                original_name = source_image_path.name
                file_stem = file_path.stem
                
                # Generate a unique filename that includes the markdown file name as prefix
                new_filename = f"{file_stem}_{original_name}"
                
                # Handle special cases for HEIC/HEIF images
                if source_image_path.suffix.lower() in ['.heic', '.heif']:
                    # Convert to PNG when copying
                    import pillow_heif
                    new_filename = f"{file_stem}_{source_image_path.stem}.png"
                    new_image_path = media_dir / new_filename
                    
                    if not new_image_path.exists():
                        try:
                            heif_file = pillow_heif.read_heif(str(source_image_path))
                            image = Image.frombytes(
                                heif_file.mode,
                                heif_file.size,
                                heif_file.data,
                                "raw",
                                heif_file.mode,
                                heif_file.stride,
                            )
                            image.save(new_image_path, 'PNG')
                            nova_console.process_item(f"Converted and copied image: {source_image_path} -> {new_image_path}")
                        except Exception as e:
                            nova_console.warning(f"Failed to convert HEIC image {source_image_path}: {str(e)}")
                            # Try using PIL's built-in HEIC support as fallback
                            try:
                                image = Image.open(source_image_path)
                                image.save(new_image_path, 'PNG')
                                nova_console.process_item(f"Converted and copied image using PIL: {source_image_path} -> {new_image_path}")
                            except Exception as e2:
                                nova_console.error(f"Failed to convert HEIC image using PIL {source_image_path}: {str(e2)}")
                                return f"![{alt_text}]({image_path})"
                else:
                    # For other formats, just copy the file
                    new_image_path = media_dir / new_filename
                    
                    if not new_image_path.exists():
                        shutil.copy2(source_image_path, new_image_path)
                        nova_console.process_item(f"Copied image: {source_image_path} -> {new_image_path}")
                
                media_files.append(new_image_path)
                return f"![{alt_text}](_media/{new_filename})"
            
            # If image not found, try to find similar filenames
            similar_files = []
            for path in search_paths:
                if path.parent.exists():
                    for file in path.parent.glob('*'):
                        if file.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.heic', '.svg')):
                            if image_name.lower() in file.name.lower():
                                similar_files.append(file)
            
            if similar_files:
                # Use the first similar file found
                source_image_path = similar_files[0]
                nova_console.process_item(f"Found similar image: {source_image_path}")
                
                new_filename = source_image_path.name
                if (media_dir / new_filename).exists():
                    new_filename = f"{file_path.stem}_{new_filename}"
                
                new_image_path = media_dir / new_filename
                
                if not new_image_path.exists():
                    shutil.copy2(source_image_path, new_image_path)
                    nova_console.process_item(f"Copied similar image: {source_image_path} -> {new_image_path}")
                
                media_files.append(new_image_path)
                return f"![{alt_text}](_media/{new_filename})"
            
            nova_console.warning(f"Image not found for {file_path.name}: {image_path}")
            return f"![{alt_text}]({image_path})"
            
        except Exception as e:
            nova_console.warning(f"Failed to process image {image_path}: {str(e)}")
            return f"![{alt_text}]({image_path})"
    
    # Handle local image references
    content = re.sub(r'!\[([^\]]*)\]\(([^:\)]+)\)', replace_local_image, content)
    
    return content, media_files

def process_file(file_path: Path, media_dir: Path) -> MarkdownFile:
    """Process a single markdown file."""
    try:
        # Read file content
        content = file_path.read_text(encoding='utf-8')
        
        # Clean up special characters
        content = content.replace('\u2028', '\n')  # Line separator
        content = content.replace('\u2029', '\n')  # Paragraph separator
        content = content.replace('\r\n', '\n')    # Windows line endings
        content = content.replace('\r', '\n')      # Mac line endings
        content = re.sub(r'[\u200B-\u200D\uFEFF]', '', content)  # Zero-width spaces
        content = re.sub(r'\n{3,}', '\n\n', content)  # Multiple blank lines
        content = content.strip()  # Remove leading/trailing whitespace
        
        # Extract date from filename
        date = extract_date_from_filename(file_path.name)
        
        # Process image links and get list of media files
        processed_content, media_files = process_image_links(content, file_path, media_dir)
        
        # Create MarkdownFile object
        markdown_file = MarkdownFile(
            path=file_path,
            date=date,
            content=processed_content,
            media_files=media_files
        )
        
        return markdown_file
        
    except Exception as e:
        nova_console.error(f"Failed to process file {file_path}", str(e))
        raise

def process_input(input_path: Path, recursive: bool = False) -> List[Path]:
    """Process input path and return list of markdown files."""
    files = []
    if input_path.is_dir():
        pattern = "**/*.md" if recursive else "*.md"
        files.extend(input_path.glob(pattern))
    elif input_path.is_file() and input_path.suffix.lower() == '.md':
        files.append(input_path)
    return sorted(files)

class MarkdownConsolidator:
    """A class to consolidate multiple markdown files into a single file."""
    
    def __init__(self):
        """Initialize the markdown consolidator."""
        self.console = NovaConsole()
        
    def consolidate(self, input_files: List[Path], output_file: Path) -> None:
        """
        Consolidate multiple markdown files into a single file.
        
        Args:
            input_files: List of input markdown file paths
            output_file: Output file path
            
        Raises:
            ValueError: If input_files is empty
            FileNotFoundError: If any input file doesn't exist
        """
        if not input_files:
            raise ValueError("No input files provided")
            
        for file in input_files:
            if not file.exists():
                raise FileNotFoundError(f"Input file not found: {file}")
        
        with timed_section("Consolidating markdown files"):
            # Create output directory if it doesn't exist
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Process each file
            with output_file.open('w', encoding='utf-8') as outfile:
                for input_file in input_files:
                    self._process_file(input_file, outfile)
    
    def _process_file(self, input_file: Path, outfile) -> None:
        """Process a single markdown file and write its contents to the output file."""
        content = input_file.read_text(encoding='utf-8')
        
        # Process any image references
        content = self._process_images(content, input_file.parent)
        
        # Write to output file
        outfile.write(f"\n\n{content}\n\n")
    
    def _process_images(self, content: str, base_path: Path) -> str:
        """Process image references in the markdown content."""
        def replace_image(match):
            alt_text = match.group(1)
            image_path = match.group(2)
            
            # Convert relative path to absolute
            if not os.path.isabs(image_path):
                image_path = base_path / image_path
            
            # Verify image exists
            if not Path(image_path).exists():
                return match.group(0)
            
            # Copy image to output directory if needed
            # For now, just return the original reference
            return f"![{alt_text}]({image_path})"
        
        # Find and replace image references
        image_pattern = r'!\[(.*?)\]\((.*?)\)'
        return re.sub(image_pattern, replace_image, content)

if __name__ == "__main__":
    app()