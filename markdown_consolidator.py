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

from colors import Colors, console
from src.processors.word_to_markdown_converter import WordConverter
from src.processors.pdf_to_markdown_converter import PDFConverter

# Logging Configuration
logging.basicConfig(
    filename='markdown_consolidator.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Global Variables
SUPPORTED_MARKDOWN_EXTENSIONS = ['.md', '.markdown', '.mdown', '.mkdn', '.mkd', '.mdwn', '.mdtxt', '.mdtext', '.text', '.txt']
SUPPORTED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.heic', '.heif']
SUPPORTED_ATTACHMENT_EXTENSIONS = ['.pdf', '.docx', '.doc']

register_heif_opener()  # Register HEIF/HEIC support with Pillow

def process_input(input_path: Union[str, List[str]], recursive: bool = False) -> List[Path]:
    """Convert input to list of files to process."""
    files = []
    if isinstance(input_path, str):
        clean_path = input_path.replace('\\ ', ' ')
        path = Path(clean_path)
        Colors.info(f"Checking path: {path}")
        Colors.info(f"Path exists: {path.exists()}")
        Colors.info(f"Path is dir: {path.is_dir()}")
        
        if path.is_dir():
            # Only process markdown files in the root directory and subdirectories that aren't attachment directories
            for file_path in path.rglob('*') if recursive else path.glob('*'):
                # Skip _media directories and their contents
                if '_media' in file_path.parts:
                    continue
                    
                # Skip files in attachment directories (directories with the same name as a markdown file)
                parent_is_attachment = (
                    file_path.parent.name.endswith('.md') or 
                    file_path.parent.with_suffix('.md').exists()
                )
                if parent_is_attachment:
                    continue
                
                if file_path.is_file():
                    files.append(file_path)
                    
            Colors.info(f"Found {len(files)} files in directory")
        elif path.is_file():
            files = [path]
        else:
            files = sorted(Path().glob(clean_path))
    elif isinstance(input_path, list):
        files = [Path(f) for f in input_path]
    else:
        Colors.error("Invalid input path provided.")
        sys.exit(1)

    valid_files = []
    for file in files:
        if file.is_file() and file.suffix.lower() in SUPPORTED_MARKDOWN_EXTENSIONS:
            if os.access(file, os.R_OK):
                valid_files.append(file)
                Colors.success(f"Added file: {file.name}")
            else:
                Colors.error(f"Permission denied: {file}")
        else:
            if file.is_file():
                Colors.warning(f"Skipping unsupported file: {file.name}")
    
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

def process_markdown_with_attachments(file_path: Path, media_dir: Path) -> dict:
    """Process a markdown file and its attachments."""
    # Get the potential attachment directory
    attachment_dir = file_path.parent / file_path.stem
    
    content = []
    attachments = []
    
    # Read main markdown content
    main_content = read_markdown_file(file_path)
    content.append(main_content)
    
    # Process attachments if they exist
    if attachment_dir.is_dir():
        # Process all supported attachments
        for ext in SUPPORTED_ATTACHMENT_EXTENSIONS:
            # Use rglob to find files in subdirectories
            for attachment in sorted(attachment_dir.rglob(f'*{ext}')):
                # Skip if it's the same as the main file
                if attachment.stem == file_path.stem:
                    continue
                    
                # Skip if the attachment is actually a directory
                if not attachment.is_file():
                    Colors.warning(f"Skipping directory that ends with {ext}: {attachment}")
                    continue
                
                # Skip files in _media directories
                if '_media' in attachment.parts:
                    continue
                
                # Convert attachment based on type
                attachment_md = attachment.parent / f"{attachment.stem}.md"
                
                if not attachment_md.exists():
                    try:
                        if ext in ['.doc', '.docx']:
                            converter = WordConverter(
                                attachment, 
                                attachment_md,
                                media_dir=attachment.parent / '_media',
                                verbose=True
                            )
                            if not converter.convert():
                                Colors.error(f"Failed to convert Word document: {attachment}")
                                continue
                        elif ext == '.pdf':
                            try:
                                converter = PDFConverter()
                                markdown_content = converter.convert_pdf_to_markdown(
                                    pdf_path=attachment,
                                    output_path=attachment_md
                                )
                            except PDFConversionError as e:
                                Colors.error(f"Failed to convert PDF: {attachment} - {str(e)}")
                                continue
                    except Exception as e:
                        Colors.error(f"Error converting {attachment}: {str(e)}")
                        continue
                
                # Add attachment header
                attachment_title = attachment.stem
                if attachment_title.endswith(('-201124-160745', '-201124-160841')):
                    attachment_title = attachment_title.rsplit('-', 2)[0]
                if attachment_title.endswith(' 2'):
                    attachment_title = attachment_title[:-2]
                
                content.append(f"\n#### {attachment_title}\n")
                
                # Read and append attachment content
                attachment_content = read_markdown_file(attachment_md)
                content.append(attachment_content)
                
                # Track attachment for TOC
                attachments.append(attachment_title)
    
    return {
        'file_identifier': file_path.stem,
        'content': '\n'.join(content),
        'attachments': attachments
    }

def combine_files(processed_files: List[dict], start_time: datetime) -> str:
    """Combine all processed content with improved TOC structure."""
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
        # Add main file to TOC
        file_id = file_data['file_identifier']
        toc.append(f"- [{file_id}](#{file_id.lower().replace(' ', '-').replace('.', '')})")
        
        # Add attachments to TOC if any
        if file_data['attachments']:
            toc.extend([
                f"  - [{attachment}](#{attachment.lower().replace(' ', '-').replace('.', '')})"
                for attachment in file_data['attachments']
            ])
        
        # Add content
        file_header = f"## {file_id}"
        combined_content.append(file_header)
        combined_content.append(file_data['content'])

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
    """Combine multiple markdown files into one optimized file."""
    try:
        output_path = Path(output_file)
        media_dir = get_media_dir(output_path)
        
        start_time = datetime.now()
        Colors.header("Analyzing Input Files")
        files_to_process = process_input(input_path, recursive)
        
        if not files_to_process:
            Colors.error("No valid markdown files found to process.")
            sys.exit(1)

        Colors.success(f"Found {len(files_to_process)} files to process.")
        Colors.header("\nProcessing Files")

        processed_files = []
        for idx, file_path in enumerate(files_to_process, 1):
            formatted_path = format_path(file_path)
            Colors.info(f"[{idx}/{len(files_to_process)}] Processing: {formatted_path}")
            content = read_markdown_file(file_path)
            if content:
                processed = process_markdown_with_attachments(file_path, media_dir)
                processed_files.append(processed)

        if not processed_files:
            Colors.error("No files were processed successfully.")
            sys.exit(1)

        Colors.header("\nGenerating Output")
        Colors.info("Consolidating content...")
        consolidated_content = combine_files(processed_files, start_time)
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(consolidated_content)
                f.flush()
                os.fsync(f.fileno())
            Colors.success(f"Output saved to: {format_path(Path(output_file))}")
            logging.info(f"Successfully wrote consolidated file to {output_file}")
            
            duration = datetime.now() - start_time
            Colors.success(f"Processing complete in {duration.total_seconds():.2f} seconds")
            sys.exit(0)
        except Exception as e:
            Colors.error(f"Failed to write output file: {e}")
            logging.error(f"Failed to write output file: {e}")
            sys.exit(1)

    except Exception as e:
        Colors.error(f"Failed to process markdown files: {e}")
        logging.error(f"Failed to process markdown files: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()