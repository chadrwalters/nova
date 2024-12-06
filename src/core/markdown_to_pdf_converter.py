#!/usr/bin/env python3

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import markdown
import jinja2
from weasyprint import HTML, CSS
import re
import hashlib
import base64
import tempfile
from PIL import Image
import pillow_heif
import io
import time
import structlog
from contextlib import contextmanager
import signal
import yaml
from datetime import datetime
from bs4 import BeautifulSoup
from pypdf import PdfMerger
from tqdm import tqdm

from src.utils.colors import NovaConsole
from src.utils.timing import timed_section
from src.utils.path_utils import normalize_path, format_path

import typer

# Initialize console
nova_console = NovaConsole()

# Initialize typer app
app = typer.Typer()

# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(indent=2)
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

class TimeoutError(Exception):
    pass

@contextmanager
def timeout(seconds: int):
    def signal_handler(signum, frame):
        raise TimeoutError("PDF generation timed out")
    
    # Register the signal handler
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

class PDFConverter:
    def __init__(self):
        """Initialize the PDF converter."""
        self.media_dir = None
        self.template_dir = None
        self.template_env = None
        self.template = None
        
    def setup(self, media_dir: Path, template_dir: Path):
        """Set up the converter with media and template directories."""
        self.media_dir = media_dir
        self.template_dir = template_dir
        self.template_env = self._setup_jinja_env()
        try:
            self.template = self.template_env.get_template('default.html')
            nova_console.process_item(f"Successfully loaded template: default.html")
        except jinja2.TemplateNotFound:
            nova_console.error(f"Template 'default.html' not found in {self.template_dir}")
            raise
        except Exception as e:
            nova_console.error(f"Failed to load template: {str(e)}")
            raise

    def _setup_jinja_env(self) -> jinja2.Environment:
        """Set up the Jinja2 environment."""
        try:
            if not self.template_dir.exists():
                nova_console.error(f"Template directory not found: {self.template_dir}")
                raise FileNotFoundError(f"Template directory not found: {self.template_dir}")

            # Create Jinja2 environment with absolute path
            env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(str(self.template_dir.absolute())),
                autoescape=True
            )
            
            # Add custom filters
            env.filters['format_date'] = lambda d: d.strftime('%Y-%m-%d') if d else ''
            
            nova_console.process_item(f"Loading templates from: {self.template_dir.absolute()}")
            return env
            
        except Exception as e:
            nova_console.error(f"Failed to setup Jinja environment: {str(e)}")
            raise

def resolve_image_path(image_path: str, base_dir: Path, media_dir: Path) -> Optional[Path]:
    """Resolve image path to actual file location."""
    try:
        # Clean up the path
        clean_path = image_path.replace('_media/', '')
        image_name = Path(clean_path).name
        
        # Try different possible locations
        search_paths = [
            # 1. Direct path from base directory
            base_dir / clean_path,
            # 2. In media directory
            media_dir / image_name,
            # 3. In _media subdirectory
            base_dir / '_media' / image_name,
            # 4. Try in base directory
            base_dir / image_name,
            # 5. Try in parent directory
            base_dir.parent / image_name,
            # 6. Try in markdown file's directory
            base_dir / base_dir.stem / image_name,
            # 7. Try in markdown file's _media directory
            base_dir / base_dir.stem / '_media' / image_name,
            # 8. Try in the markdown file's directory with original path
            base_dir / base_dir.stem / clean_path,
            # 9. Try in the markdown file's directory with original filename
            base_dir / base_dir.stem / Path(clean_path).name,
            # 10. Try in the markdown file's _media directory with original filename
            base_dir / base_dir.stem / "_media" / Path(clean_path).name
        ]
        
        for path in search_paths:
            if path.exists():
                nova_console.process_item(f"Found image at: {path}")
                return path
        
        nova_console.warning(f"Image not found: {image_path}")
        return None
        
    except Exception as e:
        nova_console.warning(f"Failed to resolve image path {image_path}: {str(e)}")
        return None

def process_image_for_web(image_path: Path, media_dir: Path) -> Optional[str]:
    """Process image for web compatibility."""
    try:
        # Get image format
        img_format = image_path.suffix.lower()
        
        # Handle HEIC/HEIF images
        if img_format in ['.heic', '.heif']:
            # Convert to PNG
            output_path = media_dir / f"{image_path.stem}.png"
            if not output_path.exists():
                heif_file = pillow_heif.read_heif(str(image_path))
                image = Image.frombytes(
                    heif_file.mode,
                    heif_file.size,
                    heif_file.data,
                    "raw",
                    heif_file.mode,
                    heif_file.stride,
                )
                image.save(output_path, 'PNG')
                nova_console.process_item(f"Converted HEIC image: {image_path} -> {output_path}")
            return str(output_path)
        
        elif img_format == '.svg':
            nova_console.warning(f"SVG conversion not available - using original: {image_path}")
            return str(image_path)
        
        # For other formats, just return the path
        return str(image_path)
        
    except Exception as e:
        nova_console.warning(f"Failed to process image {image_path}: {str(e)}")
        return None

def process_markdown_content(content: str, base_dir: Path, media_dir: Path) -> str:
    """Process markdown content to handle images and other elements."""
    
    def replace_image_path(match):
        alt_text = match.group(1)
        image_path = match.group(2)
        
        try:
            resolved_path = resolve_image_path(image_path, base_dir, media_dir)
            if resolved_path:
                # Convert image if needed and get web-safe path
                processed_path = process_image_for_web(resolved_path, media_dir)
                if processed_path:
                    return f'![{alt_text}]({processed_path})'
            
            # If image not found or processing failed, keep original
            return match.group(0)
            
        except Exception as e:
            nova_console.warning(f"Failed to process image {image_path}: {str(e)}")
            return match.group(0)
    
    # Process image links
    content = re.sub(r'!\[([^\]]*)\]\(([^:\)]+)\)', replace_image_path, content)
    
    return content

@app.command()
def convert_markdown_to_pdf(
    input_file: str = typer.Argument(..., help="Input markdown file path"),
    output_file: str = typer.Argument(..., help="Output PDF file path"),
    media_dir: str = typer.Argument(..., help="Media directory path"),
    template_dir: str = typer.Argument(..., help="Template directory path")
) -> None:
    """Convert markdown to PDF with proper image handling."""
    try:
        # Convert string paths to Path objects
        input_path = Path(input_file)
        output_path = Path(output_file)
        media_path = Path(media_dir)
        template_path = Path(template_dir)
        
        # Initialize and setup PDF converter
        converter = PDFConverter()
        converter.setup(media_path, template_path)
        
        # Read markdown content
        content = input_path.read_text(encoding='utf-8')
        
        # Process content
        processed_content = process_markdown_content(content, input_path.parent, media_path)
        
        # Convert to HTML
        html = markdown.markdown(
            processed_content,
            extensions=['tables', 'fenced_code', 'codehilite']
        )
        
        # Prepare template variables
        template_vars = {
            'title': input_path.stem,
            'content': html,
            'date': datetime.now().strftime('%Y-%m-%d')
        }
        
        # Render template
        rendered_html = converter.template.render(**template_vars)
        
        # Convert to PDF using WeasyPrint 59.0 compatible initialization
        html_doc = HTML(string=rendered_html, base_url=str(media_path.absolute()))
        html_doc.write_pdf(str(output_path))
        
        nova_console.success(f"PDF generated successfully: {output_path}")
        
    except Exception as e:
        nova_console.error(f"Failed to convert markdown to PDF", str(e))
        raise typer.Exit(1)

if __name__ == "__main__":
    app()