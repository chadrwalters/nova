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

class MarkdownToPDFConverter:
    """A class to convert markdown files to PDF."""
    
    def __init__(self, template_path: Optional[Path] = None, css_path: Optional[Path] = None):
        """
        Initialize the PDF converter.
        
        Args:
            template_path: Optional path to a custom HTML template
            css_path: Optional path to a custom CSS file
        """
        self.template_path = template_path
        self.css_path = css_path
        self._setup_jinja()
        
    def _setup_jinja(self):
        """Set up the Jinja2 environment."""
        if self.template_path and not self.template_path.exists():
            raise FileNotFoundError(f"Template file not found: {self.template_path}")
        
        template_dir = Path(__file__).parent.parent / "resources" / "templates"
        if not template_dir.exists():
            raise FileNotFoundError(f"Template directory not found: {template_dir}")
        
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(template_dir))
        )
        
    def _get_template(self) -> jinja2.Template:
        """
        Get the HTML template to use.
        
        Returns:
            jinja2.Template: The template to use for rendering
        
        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        if self.template_path:
            if not self.template_path.exists():
                raise FileNotFoundError(f"Template file not found: {self.template_path}")
            with self.template_path.open('r', encoding='utf-8') as f:
                return jinja2.Template(f.read())
        return self.jinja_env.get_template('default.html')
        
    def _get_css(self) -> Optional[List[CSS]]:
        """Get CSS stylesheets to use."""
        css_files = []
        
        # Add custom CSS if provided
        if self.css_path and self.css_path.exists():
            css_files.append(CSS(filename=str(self.css_path)))
            
        # Add default CSS
        default_css = Path(__file__).parent.parent / "resources" / "styles" / "default.css"
        if default_css.exists():
            css_files.append(CSS(filename=str(default_css)))
            
        return css_files if css_files else None

    def convert(self, input_file: Path, output_file: Path) -> None:
        """
        Convert a markdown file to PDF.
        
        Args:
            input_file: Input markdown file path
            output_file: Output PDF file path
            
        Raises:
            FileNotFoundError: If input file doesn't exist
        """
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
            
        # Create output directory if needed
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert markdown to HTML
        md = markdown.Markdown(extensions=['extra'])
        with input_file.open('r', encoding='utf-8') as f:
            content = f.read()
            html_content = md.convert(content)
        
        # Apply template
        template = self._get_template()
        template_vars = {
            'title': input_file.stem,
            'content': html_content,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        html = template.render(**template_vars)
        
        # Convert to PDF
        css = self._get_css()
        HTML(string=html).write_pdf(
            output_file,
            stylesheets=css if css else []
        )

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

def convert_markdown_to_pdf(input_file: str, output_file: str, media_dir: str, template_dir: str) -> None:
    """
    Convert a markdown file to PDF.
    
    Args:
        input_file: Path to input markdown file
        output_file: Path to output PDF file
        media_dir: Path to media directory
        template_dir: Path to template directory
    """
    input_path = Path(input_file)
    output_path = Path(output_file)
    media_path = Path(media_dir)
    template_path = Path(template_dir)
    
    try:
        with timed_section("Converting markdown to PDF"):
            # Initialize converter with template directory
            converter = MarkdownToPDFConverter()
            
            # Process content to handle images
            content = input_path.read_text(encoding='utf-8')
            processed_content = process_markdown_content(
                content,
                input_path.parent,
                media_path
            )
            
            # Write processed content to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', encoding='utf-8', delete=False) as temp_file:
                temp_file.write(processed_content)
                temp_path = Path(temp_file.name)
            
            try:
                # Convert to PDF with timeout
                with timeout(300):  # 5 minutes timeout
                    converter.convert(temp_path, output_path)
                nova_console.success(f"Successfully converted {input_file} to {output_file}")
            finally:
                # Clean up temporary file
                temp_path.unlink()
                
    except TimeoutError:
        nova_console.error("PDF conversion timed out")
        raise
    except Exception as e:
        nova_console.error(f"Failed to convert markdown to PDF: {str(e)}")
        raise

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
        converter = MarkdownToPDFConverter(template_path, None)
        
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
        rendered_html = converter._get_template().render(**template_vars)
        
        # Convert to PDF using WeasyPrint 59.0 compatible initialization
        html_doc = HTML(string=rendered_html, base_url=str(media_path.absolute()))
        html_doc.write_pdf(str(output_path))
        
        nova_console.success(f"PDF generated successfully: {output_path}")
        
    except Exception as e:
        nova_console.error(f"Failed to convert markdown to PDF", str(e))
        raise typer.Exit(1)

if __name__ == "__main__":
    app()