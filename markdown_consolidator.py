#!/usr/bin/env python3

import os
import sys
import re
import hashlib
import logging
import requests
from pathlib import Path
from typing import List, Union
from datetime import datetime
from multiprocessing import Pool

import click
from PIL import Image
from rich.console import Console
from pillow_heif import register_heif_opener
import pillow_heif
import base64
import io

# Logging Configuration
logging.basicConfig(
    filename='markdown_consolidator.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Global Variables
SUPPORTED_MARKDOWN_EXTENSIONS = ['.md', '.markdown']
SUPPORTED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.heic', '.heif']
console = Console()

register_heif_opener()  # Register HEIF/HEIC support with Pillow

def process_input(input_path: Union[str, List[str]], recursive: bool = False) -> List[Path]:
    """
    Convert input (directory/wildcard/file list) to a list of files to process.
    Sort files alphabetically, validate file types and permissions.
    Return a list of Path objects to process.
    """
    files = []
    if isinstance(input_path, str):
        path = Path(input_path)
        if path.is_dir():
            pattern = '**/*' if recursive else '*'
            files = sorted(path.glob(f'{pattern}'))
        elif path.is_file():
            files = [path]
        else:
            files = sorted(Path().glob(input_path))
    elif isinstance(input_path, list):
        files = [Path(f) for f in input_path]
    else:
        logging.error("Invalid input path provided.")
        sys.exit(1)

    valid_files = []
    for file in files:
        if file.suffix.lower() in SUPPORTED_MARKDOWN_EXTENSIONS:
            if os.access(file, os.R_OK):
                valid_files.append(file)
            else:
                logging.error(f"Permission denied: {file}")
                sys.exit(1)
        else:
            logging.warning(f"Unsupported file type: {file}")
    valid_files.sort()
    return valid_files

def read_markdown_file(file_path: Path) -> str:
    """
    Read a markdown file, handle encoding (UTF-8), and perform basic validation.
    Return file content as a string.
    """
    try:
        with file_path.open('r', encoding='utf-8') as f:
            content = f.read()
        if not content.strip():
            logging.warning(f"File is empty: {file_path}")
        return content
    except Exception as e:
        logging.error(f"Error reading {file_path}: {e}")
        return ""

def process_markdown(content: str, file_path: Path, media_dir: Path) -> dict:
    """
    Parse markdown content, update internal links, handle duplicate headers.
    Return processed content and metadata.
    """
    file_identifier = file_path.name

    # Handle duplicate headers by adding file context
    content = add_file_context_to_headers(content, file_identifier)

    # Update internal links to anchor links
    content = update_internal_links(content)

    # Process images and collect embedded media
    embedded_media = []
    content = process_images_in_markdown(content, embedded_media, file_path, media_dir)

    return {
        "file_identifier": str(file_identifier),
        "content": content,
        "embedded_media": embedded_media
    }

def add_file_context_to_headers(content: str, file_identifier: str) -> str:
    """
    Add '[from filename.md]' suffix to headers to handle duplicates.
    """
    header_pattern = r'^(#{1,6}\s*)(.+)$'
    def replace_header(match):
        header_level = match.group(1)
        header_text = match.group(2)
        new_header = f"{header_level}{header_text} [from {file_identifier}]"
        return new_header

    return re.sub(header_pattern, replace_header, content, flags=re.MULTILINE)

def update_internal_links(content: str) -> str:
    """
    Convert internal markdown links to anchor links.
    """
    link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    def replace_link(match):
        text = match.group(1)
        link = match.group(2)
        if link.startswith('#'):
            anchor = link.lower().replace(' ', '-').replace('#', '')
            return f'[{text}](#{anchor})'
        else:
            return match.group(0)
    return re.sub(link_pattern, replace_link, content)

def process_images_in_markdown(content: str, embedded_media: list, file_path: Path, media_dir: Path) -> str:
    """
    Find all images in markdown content, process them, and update paths.
    """
    image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    images_to_process = []

    def replace_image(match):
        alt_text = match.group(1)
        image_path = match.group(2)
        images_to_process.append((alt_text, image_path))
        return f'![{alt_text}]({image_path})'  # Placeholder, will be replaced later

    content = re.sub(image_pattern, replace_image, content)

    # Process images in parallel
    with Pool() as pool:
        results = pool.starmap(
            process_single_image, 
            [(alt_text, image_path, file_path, media_dir) 
             for alt_text, image_path in images_to_process]
        )

    # Replace placeholders with processed image paths
    for idx, (alt_text, processed_path) in enumerate(results):
        if processed_path:
            embedded_media.append(str(processed_path))
            try:
                # Try to create relative path
                relative_path = processed_path.relative_to(Path.cwd())
            except ValueError:
                # If that fails, just use the filename with _media prefix
                relative_path = Path('_media') / processed_path.name
            
            content = content.replace(
                f'![{alt_text}]({images_to_process[idx][1]})', 
                f'![{alt_text}]({relative_path})'
            )
        else:
            content = content.replace(
                f'![{alt_text}]({images_to_process[idx][1]})', 
                f'![{alt_text}](placeholder.jpg)'
            )

    return content

def process_single_image(alt_text: str, image_path: str, file_path: Path, media_dir: Path) -> tuple:
    """
    Helper function to process a single image.
    Handles three types of images:
    1. Local files
    2. Remote URLs
    3. Base64 encoded images
    """
    try:
        # Handle Base64 encoded images
        if image_path.startswith('data:image'):
            return process_base64_image(alt_text, image_path, media_dir)
        # Handle remote images
        elif image_path.startswith('http'):
            processed_image_path = handle_external_image(image_path, media_dir)
        # Handle local images
        else:
            image_full_path = (file_path.parent / image_path).resolve()
            processed_image_path = process_image(image_full_path, media_dir)
        return alt_text, processed_image_path
    except Exception as e:
        logging.error(f"Error processing image: {e}")
        return alt_text, None

def process_base64_image(alt_text: str, base64_string: str, media_dir: Path) -> tuple:
    """Process a Base64 encoded image."""
    try:
        # Extract the actual base64 data
        header, base64_data = base64_string.split(',', 1)
        
        # Decode base64 to binary
        binary_data = base64.b64decode(base64_data)
        
        # Create a file-like object from the binary data
        image_data = io.BytesIO(binary_data)
        
        # Generate a hash of the image data
        hash_digest = hashlib.sha256(binary_data).hexdigest()[:8]
        
        # Create new filename
        new_filename = f"base64_image_{hash_digest}.jpg"
        new_image_path = media_dir / new_filename
        
        # Open and process with Pillow
        with Image.open(image_data) as img:
            # Convert to RGB if needed
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Resize if needed
            img.thumbnail((2000, 2000), Image.LANCZOS)
            
            # Save as JPEG
            img.save(new_image_path, 'JPEG', quality=85, progressive=True)
            
        logging.info(f"Processed base64 image saved as {new_image_path}")
        return alt_text, new_image_path
        
    except Exception as e:
        logging.error(f"Error processing base64 image: {e}")
        return alt_text, None

def process_image(image_path: Path, media_dir: Path) -> Union[Path, None]:
    """Process and optimize image."""
    if not image_path.exists():
        logging.error(f"Image file not found: {image_path}")
        return None

    if image_path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        logging.warning(f"Unsupported image type: {image_path}")
        return None

    try:
        # Read image bytes for hashing
        image_bytes = image_path.read_bytes()
        hash_digest = hashlib.sha256(image_bytes).hexdigest()[:8]
        
        # Always convert to JPEG for consistency
        new_filename = f"{image_path.stem}_{hash_digest}.jpg"
        new_image_path = media_dir / new_filename

        with Image.open(image_path) as img:
            # Convert HEIC/HEIF to RGB mode
            if image_path.suffix.lower() in ['.heic', '.heif']:
                img = img.convert('RGB')
            
            # Handle other formats that might need RGB conversion
            elif img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Resize if needed
            img.thumbnail((2000, 2000), Image.LANCZOS)
            
            # Save as JPEG
            img.save(new_image_path, 'JPEG', quality=85, progressive=True)
            
        logging.info(f"Processed image saved as {new_image_path}")
        return new_image_path
        
    except Exception as e:
        logging.warning(f"Image processing error for {image_path}: {e}")
        return None

def handle_external_image(url: str, media_dir: Path) -> Union[Path, None]:
    """Download and process external image."""
    try:
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200:
            temp_image_path = media_dir / 'temp_image'
            with open(temp_image_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            processed_image = process_image(temp_image_path, media_dir)
            temp_image_path.unlink()  # Remove temporary file
            return processed_image
        else:
            logging.warning(f"Failed to download image from {url}")
            return None
    except Exception as e:
        logging.warning(f"Exception while downloading image {url}: {e}")
        return None

def combine_files(processed_files: List[dict], start_time: datetime) -> str:
    """
    Combine all processed content:
    1. Add metadata header.
    2. Generate table of contents.
    3. Add file identifiers as headers.
    4. Combine content.
    Return consolidated markdown string.
    """
    end_time = datetime.now()
    processing_duration = (end_time - start_time).total_seconds()
    metadata = {
        "generated_timestamp": end_time.isoformat(),
        "source_files": [pf['file_identifier'] for pf in processed_files],
        "processing_duration": f"{processing_duration} seconds"
    }

    # Generate Table of Contents
    toc = []
    combined_content = []
    for file_data in processed_files:
        file_header = f"## {file_data['file_identifier']}"
        combined_content.append(file_header)
        combined_content.append(file_data['content'])
        toc.append(f"- [{file_data['file_identifier']}]"
                   f"(#{file_data['file_identifier'].lower().replace(' ', '-').replace('.', '')})")

    metadata_block = '\n'.join([f"{k}: {v}" for k, v in metadata.items()])
    toc_block = '\n'.join(toc)
    output = f"---\n{metadata_block}\n---\n\n# Table of Contents\n{toc_block}\n\n"
    output += '\n\n'.join(combined_content)
    return output

def get_media_dir(output_file: Path) -> Path:
    """
    Get the media directory path based on the output file location.
    Creates the directory if it doesn't exist.
    """
    media_dir = output_file.parent / '_media'
    media_dir.mkdir(exist_ok=True)
    return media_dir

def format_path(path: Path) -> str:
    """Format path for cleaner console output."""
    try:
        # Try to get relative path first
        relative = path.relative_to(Path.cwd())
        return str(relative)
    except ValueError:
        # If relative path fails, return a cleaned absolute path
        return str(path).replace(str(Path.home()), '~')

@click.command()
@click.argument('input_path', type=str, required=True)
@click.argument('output_file', type=str, required=True)
@click.option('--recursive', is_flag=True, help='Process directories recursively')
@click.option('--log-file', type=str, help='Custom log file location')
@click.option('--verbose', is_flag=True, help='Increase output verbosity')
def main(input_path, output_file, recursive, log_file, verbose):
    """
    Combine multiple markdown files into one optimized file.
    """
    # Convert output_file to Path and create media directory
    output_path = Path(output_file)
    media_dir = get_media_dir(output_path)
    
    # Configure Logging
    if log_file:
        logging.getLogger().handlers = []
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    if verbose:
        console.log("[bold blue]Verbose mode activated.[/]")
        logging.getLogger().setLevel(logging.DEBUG)

    start_time = datetime.now()
    console.rule("[bold blue]Starting Markdown Consolidation[/]")

    files_to_process = process_input(input_path, recursive)
    if not files_to_process:
        console.print("[bold red]No valid markdown files found to process.[/]")
        sys.exit(1)

    console.print(f"\nFound [bold green]{len(files_to_process)}[/] files to process.\n")

    processed_files = []
    with console.status("[bold green]Processing files...") as status:
        for idx, file_path in enumerate(files_to_process, 1):
            formatted_path = format_path(file_path)
            console.print(f"[{idx}/{len(files_to_process)}] [bold cyan]{formatted_path}[/]")
            content = read_markdown_file(file_path)
            if content:
                processed = process_markdown(content, file_path, media_dir)
                processed_files.append(processed)

    if not processed_files:
        console.print("[bold red]No files were processed successfully.[/]")
        sys.exit(1)

    console.print("\n[bold green]Generating consolidated output...[/]")
    consolidated_content = combine_files(processed_files, start_time)
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(consolidated_content)
        console.print(f"[bold green]✓[/] Output saved to: [bold cyan]{format_path(Path(output_file))}[/]")
        logging.info(f"Successfully wrote consolidated file to {output_file}")
    except Exception as e:
        console.print(f"[bold red]✗ Failed to write output file: {e}[/]")
        logging.error(f"Failed to write output file: {e}")

    duration = datetime.now() - start_time
    console.rule("[bold blue]Processing Complete[/]")
    console.print(f"[bold green]Total time: {duration.total_seconds():.2f} seconds[/]")

if __name__ == '__main__':
    main()