#!/usr/bin/env python3

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml
import markdown
import jinja2
from weasyprint import HTML, CSS
from bs4 import BeautifulSoup
from datetime import datetime
import signal
from contextlib import contextmanager
import re
import hashlib
import base64
import tempfile
from pypdf import PdfMerger
from PIL import Image
import io
from tqdm import tqdm
import time
import structlog

from src.utils.colors import NovaConsole
from src.utils.timing import timed_section
from src.utils.path_utils import normalize_path, format_path

# Initialize console
nova_console = NovaConsole()

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
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize PDF converter with optional config."""
        self.config = self.load_config(config_path)
        self.template_env = self.setup_jinja()
        self.media_dir = Path(os.getenv('NOVA_CONSOLIDATED_DIR', '.')) / '_media'
        self.media_dir.mkdir(parents=True, exist_ok=True)
        
    def load_config(self, config_path: Optional[Path]) -> Dict[Any, Any]:
        """Load configuration from YAML file."""
        default_config = {
            'template': 'default_template.html',
            'style': 'default_style.css',
            'pdf': {
                'margin': '1in',
                'page-size': 'Letter'
            },
            'pdf_timeout': int(os.getenv('PDF_TIMEOUT', 300))
        }
        
        if not config_path:
            return default_config
            
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
            return {**default_config, **config}
        except Exception as e:
            nova_console.warning(f"Failed to load config: {e}. Using defaults.")
            return default_config
            
    def setup_jinja(self) -> jinja2.Environment:
        """Setup Jinja2 environment."""
        try:
            template_dir = Path(__file__).parent.parent / 'resources' / 'templates'
            if not template_dir.exists():
                raise FileNotFoundError(f"Template directory not found: {template_dir}")
            
            nova_console.process_item(f"Loading templates from: {template_dir}")
            env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(str(template_dir)),
                autoescape=True
            )
            
            # Verify template exists
            template_path = template_dir / self.config['template']
            if not template_path.exists():
                raise FileNotFoundError(f"Template file not found: {template_path}")
                
            return env
            
        except Exception as e:
            nova_console.error("Failed to setup Jinja environment", str(e))
            raise
        
    @timed_section("Loading content")
    def load_content(self, input_file: Path) -> str:
        """Load and clean content from file."""
        content = input_file.read_text(encoding='utf-8')
        return self.clean_content(content)
        
    @timed_section("Converting markdown")
    def convert_markdown(self, content: str) -> str:
        """Convert markdown to HTML with proper extensions."""
        # Initialize markdown converter with all required extensions
        md = markdown.Markdown(extensions=[
            'markdown.extensions.extra',        # Tables, code blocks, etc
            'markdown.extensions.codehilite',   # Code highlighting
            'markdown.extensions.fenced_code',  # Fenced code blocks
            'markdown.extensions.tables',       # Tables
            'markdown.extensions.toc',          # Table of contents
            'markdown.extensions.sane_lists',   # Better list handling
            'markdown.extensions.smarty',       # Smart quotes
            'markdown.extensions.meta',         # Metadata
            'markdown.extensions.attr_list',    # Attribute lists
            'markdown.extensions.def_list',     # Definition lists
            'markdown.extensions.footnotes'     # Footnotes
        ])
        
        # Convert markdown to HTML
        html = md.convert(content)
        
        # Clean up the HTML
        soup = BeautifulSoup(html, 'html.parser')
        
        # Fix code blocks
        for pre in soup.find_all('pre'):
            # Ensure code blocks have proper classes
            if not pre.find('code'):
                code = soup.new_tag('code')
                code.string = pre.string
                pre.string = ''
                pre.append(code)
            
            # Wrap in a div for better page breaks
            wrapper = soup.new_tag('div', attrs={'class': 'code-block'})
            pre.wrap(wrapper)
        
        # Fix headers
        for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            # Add section wrapper for better page breaks
            if tag.name in ['h1', 'h2']:
                section = soup.new_tag('section')
                tag.wrap(section)
                
                # Move content until next header of same or higher level into section
                next_tag = section
                while next_tag.next_sibling:
                    next_tag = next_tag.next_sibling
                    if next_tag.name in ['h1', 'h2']:
                        break
                    next_tag.wrap(section)
        
        # Fix lists
        for list_tag in soup.find_all(['ul', 'ol']):
            # Add wrapper for better page breaks
            wrapper = soup.new_tag('div', attrs={'class': 'list-wrapper'})
            list_tag.wrap(wrapper)
        
        # Fix tables
        for table in soup.find_all('table'):
            # Add wrapper for better page breaks
            wrapper = soup.new_tag('div', attrs={'class': 'table-wrapper'})
            table.wrap(wrapper)
        
        # Fix images
        for img in soup.find_all('img'):
            # Add wrapper for better page breaks
            wrapper = soup.new_tag('div', attrs={'class': 'image-wrapper'})
            img.wrap(wrapper)
            
            # Add figure and caption if alt text exists
            if img.get('alt'):
                figure = soup.new_tag('figure')
                wrapper.wrap(figure)
                figcaption = soup.new_tag('figcaption')
                figcaption.string = img['alt']
                figure.append(figcaption)
        
        return str(soup)
        
    @timed_section("Generating PDF")
    def generate_pdf(self, html: str, output_file: Path, css: CSS) -> None:
        """Generate PDF with improved memory management."""
        try:
            html_size_mb = len(html) / (1024 * 1024)
            print(f"\nProcessing {html_size_mb:.1f}MB of HTML content...")
            
            # Optimize images before PDF generation
            html = self.optimize_images(html)
            
            # Split large documents into chunks if needed
            if html_size_mb > 10:  # Split if larger than 10MB
                print("Large document detected - processing in chunks...")
                pdfs = self.generate_pdf_in_chunks(html, output_file, css)
                self.merge_pdfs(pdfs, output_file)
            else:
                timeout_value = self.config.get('pdf_timeout', 300)
                print(f"PDF generation timeout set to {timeout_value} seconds")
                
                with timeout(timeout_value):
                    HTML(string=html).write_pdf(
                        output_file,
                        stylesheets=[css] if css else None,
                        **self.config['pdf']
                    )
                
            # Verify the PDF was created successfully
            pdf_path = Path(output_file)
            if pdf_path.exists():
                pdf_size = pdf_path.stat().st_size / (1024 * 1024)
                print(f"✓ PDF generated successfully ({pdf_size:.1f}MB)")
            else:
                raise RuntimeError("PDF file was not created")
                
        except TimeoutError:
            print(f"\n⚠️  PDF generation timed out after {self.config['pdf_timeout']} seconds.")
            print("Try increasing the PDF_TIMEOUT value in your .env file")
            raise
        except KeyboardInterrupt:
            print("\n⚠️  PDF generation cancelled by user")
            # Clean up partial PDF file if it exists
            Path(output_file).unlink(missing_ok=True)
            raise
        except Exception as e:
            print(f"\n⚠️  Error generating PDF: {str(e)}")
            raise

    def convert(self, input_file: Path, output_file: Path) -> bool:
        """Convert markdown to PDF."""
        try:
            # Configure logging
            structlog.configure(
                processors=[
                    structlog.processors.add_log_level,
                    structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
                    structlog.dev.ConsoleRenderer(colors=True)
                ],
                wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
                context_class=dict,
                logger_factory=structlog.PrintLoggerFactory(),
                cache_logger_on_first_use=False
            )
            
            # Ensure output directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Start conversion
            nova_console.process_start("PDF conversion", str(input_file))
            
            # Load and convert content
            content = self.load_content(input_file)
            html = self.convert_markdown(content)
            
            # Generate PDF
            template = self.template_env.get_template(self.config['template'])
            context = {
                'content': html,
                'title': input_file.stem,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            rendered = template.render(**context)
            rendered = self.clean_html(rendered)
            
            style_path = Path(__file__).parent.parent / 'resources' / 'styles' / self.config['style']
            css = CSS(filename=str(style_path))
            
            self.generate_pdf(rendered, output_file, css)
            
            # Show completion stats
            size_mb = output_file.stat().st_size / (1024 * 1024)
            nova_console.process_complete("PDF conversion", {
                "Output": str(output_file),
                "Size": f"{size_mb:.1f}MB"
            })
            return True
            
        except Exception as e:
            nova_console.error("PDF conversion failed", str(e))
            return False

    def clean_content(self, content: str) -> str:
        """Clean markdown content of problematic characters."""
        # Replace Unicode line separators with standard newlines
        content = content.replace('\u2028', '\n').replace('\u2029', '\n')
        
        # Normalize line endings
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove zero-width spaces and other invisible characters
        content = re.sub(r'[\u200B-\u200D\uFEFF]', '', content)
        
        # Fix duplicate headers
        lines = content.split('\n')
        seen_headers = set()
        cleaned_lines = []
        
        for line in lines:
            if line.startswith('#'):
                header = line.strip()
                if header in seen_headers:
                    continue
                seen_headers.add(header)
            cleaned_lines.append(line)
        
        content = '\n'.join(cleaned_lines)
        
        # Normalize heading structures (ensure proper hierarchy)
        headers = []
        current_level = 0
        
        def get_header_level(line):
            match = re.match(r'^(#{1,6})\s', line)
            return len(match.group(1)) if match else 0
        
        lines = content.split('\n')
        for i, line in enumerate(lines):
            level = get_header_level(line)
            if level > 0:
                if level > current_level + 1:
                    # Header level jumped too much, normalize it
                    level = current_level + 1
                    lines[i] = '#' * level + line[line.find(' '):]
                current_level = level
        
        content = '\n'.join(lines)
        
        # Ensure proper spacing around headers
        content = re.sub(r'\n{3,}#', '\n\n#', content)
        content = re.sub(r'#[^\n]+\n{3,}', lambda m: m.group().rstrip() + '\n\n', content)
        
        # Clean up list formatting
        content = re.sub(r'^\s*[-*+]\s+', '* ', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*\d+\.\s+', '1. ', content, flags=re.MULTILINE)
        
        return content

    def extract_base64_images(self, content: str) -> str:
        """Extract base64 images to files and replace with standard markdown links."""
        image_pattern = r'!\[([^\]]*)\]\(data:image/([^;]+);base64,([^\)]+)\)'
        
        def save_and_replace(match):
            alt_text = match.group(1)
            image_type = match.group(2)
            base64_data = match.group(3)
            
            # Generate hash of image data for filename
            filename = f"image_{hashlib.md5(base64_data.encode()).hexdigest()}.{image_type}"
            filepath = self.media_dir / filename
            
            # Save image file
            image_data = base64.b64decode(base64_data)
            filepath.write_bytes(image_data)
            
            # Return markdown link to saved file
            return f'![{alt_text}](_media/{filename})'
            
        return re.sub(image_pattern, save_and_replace, content)

    def clean_html(self, html: str) -> str:
        """Clean HTML content before PDF generation."""
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove empty paragraphs
        for p in soup.find_all('p'):
            if not p.get_text(strip=True):
                p.decompose()
        
        # Ensure proper spacing
        return str(soup.prettify())

    def generate_pdf_in_chunks(self, html: str, output_file: Path, css: CSS) -> List[Path]:
        """Split HTML content into chunks and generate PDFs."""
        chunk_size = int(os.getenv('PDF_CHUNK_SIZE', 10)) * 1024 * 1024  # Convert MB to bytes
        soup = BeautifulSoup(html, 'lxml')
        sections = soup.find_all(['h1', 'h2', 'h3'])
        
        if not sections:
            # If no headers found, split by paragraphs
            sections = soup.find_all('p')
            
        chunks = []
        current_chunk = []
        current_size = 0
        
        # Create temporary directory for chunk PDFs
        temp_dir = Path(tempfile.mkdtemp())
        chunk_pdfs = []
        
        for section in sections:
            # Get all content until next section
            content = []
            current = section
            while current and current.next_sibling:
                current = current.next_sibling
                if current.name in ['h1', 'h2', 'h3']:
                    break
                content.append(str(current))
                
            section_html = str(section) + ''.join(content)
            section_size = len(section_html)
            
            if current_size + section_size > chunk_size and current_chunk:
                # Process current chunk
                chunk_html = ''.join(current_chunk)
                chunk_pdf = self.process_chunk(chunk_html, temp_dir, len(chunk_pdfs), css)
                chunk_pdfs.append(chunk_pdf)
                current_chunk = []
                current_size = 0
                
            current_chunk.append(section_html)
            current_size += section_size
            
        # Process final chunk
        if current_chunk:
            chunk_html = ''.join(current_chunk)
            chunk_pdf = self.process_chunk(chunk_html, temp_dir, len(chunk_pdfs), css)
            chunk_pdfs.append(chunk_pdf)
            
        return chunk_pdfs
        
    def process_chunk(self, html: str, temp_dir: Path, chunk_num: int, css: CSS) -> Path:
        """Process a single HTML chunk into a PDF."""
        chunk_file = temp_dir / f"chunk_{chunk_num}.pdf"
        print(f"Processing chunk {chunk_num + 1}...")
        
        timeout_value = self.config.get('pdf_timeout', 300)
        with timeout(timeout_value):
            HTML(string=html).write_pdf(
                chunk_file,
                stylesheets=[css] if css else None,
                **self.config['pdf']
            )
            
        return chunk_file
        
    def merge_pdfs(self, pdf_files: List[Path], output_file: Path) -> None:
        """Merge multiple PDF files into one."""
        print(f"\nMerging {len(pdf_files)} PDF chunks...")
        merger = PdfMerger()
        
        try:
            for pdf in pdf_files:
                merger.append(str(pdf))
                
            merger.write(str(output_file))
            merger.close()
            
            # Clean up temporary files
            for pdf in pdf_files:
                pdf.unlink()
            pdf_files[0].parent.rmdir()  # Remove temp directory
            
        except Exception as e:
            print(f"\n⚠️  Error merging PDFs: {str(e)}")
            raise

    def optimize_images(self, html_content: str) -> str:
        """Optimize images in HTML content with detailed timing logs."""
        start_time = time.time()
        soup = BeautifulSoup(html_content, 'html.parser')
        images = soup.find_all('img')
        
        nova_console.process_item(f"Starting image optimization - Found {len(images)} images")
        
        # Get the media directory from the environment
        consolidated_dir = Path(os.getenv('NOVA_CONSOLIDATED_DIR', '.'))
        media_dir = consolidated_dir / '_media'
        nova_console.process_item(f"Using media directory: {media_dir}")
        
        for idx, img in enumerate(images, 1):
            try:
                img_start = time.time()
                image_path = img['src']
                
                # Skip already embedded images
                if image_path.startswith('data:image'):
                    nova_console.process_item(f"Skipping already embedded image {idx}/{len(images)}")
                    continue
                
                # Handle file:// protocol
                if image_path.startswith('file://'):
                    image_path = image_path[7:]
                
                # Convert relative path to absolute
                if not Path(image_path).is_absolute():
                    if image_path.startswith('_media/'):
                        image_path = str(media_dir / Path(image_path).name)
                    else:
                        image_path = str(media_dir / image_path)
                    nova_console.process_item(f"Resolved image path: {image_path}")

                # Check if file exists before processing
                if not os.path.exists(image_path):
                    nova_console.warning(f"Image not found at path: {image_path}")
                    continue
                
                # Get original file info
                original_bytes = os.path.getsize(image_path)
                
                # Try to optimize the image
                try:
                    with Image.open(image_path) as img_file:
                        original_size = img_file.size
                        
                        # Convert to RGB if needed
                        if img_file.mode in ('RGBA', 'LA'):
                            background = Image.new('RGB', img_file.size, (255, 255, 255))
                            if img_file.mode == 'RGBA':
                                background.paste(img_file, mask=img_file.split()[3])
                            else:
                                background.paste(img_file, mask=img_file.split()[1])
                            img_file = background
                        elif img_file.mode != 'RGB':
                            img_file = img_file.convert('RGB')
                        
                        # Resize if too large
                        if img_file.size[0] > 1500 or img_file.size[1] > 1500:
                            img_file.thumbnail((1500, 1500))
                        
                        # Try optimizing
                        buffer = io.BytesIO()
                        img_file.save(buffer, format='JPEG', quality=85, optimize=True)
                        compressed_bytes = len(buffer.getvalue())
                        
                        # Only use optimized version if it's smaller
                        if compressed_bytes < original_bytes:
                            base64_img = base64.b64encode(buffer.getvalue()).decode()
                            img['src'] = f"data:image/jpeg;base64,{base64_img}"
                            
                            img_time = time.time() - img_start
                            nova_console.process_item(
                                f"Image {idx}/{len(images)} optimized: "
                                f"{original_size[0]}x{original_size[1]}, "
                                f"{original_bytes/1024:.1f}KB → {compressed_bytes/1024:.1f}KB "
                                f"({(compressed_bytes/original_bytes)*100:.1f}%), "
                                f"{img_time:.2f}s"
                            )
                        else:
                            # Use original if optimization didn't help
                            with open(image_path, 'rb') as f:
                                base64_img = base64.b64encode(f.read()).decode()
                                img['src'] = f"data:image/jpeg;base64,{base64_img}"
                            
                            img_time = time.time() - img_start
                            nova_console.process_item(
                                f"Image {idx}/{len(images)} embedded without optimization: "
                                f"{original_size[0]}x{original_size[1]}, "
                                f"{original_bytes/1024:.1f}KB (optimization skipped), "
                                f"{img_time:.2f}s"
                            )
                
                except Exception as e:
                    # If optimization fails, try to use original file
                    try:
                        with open(image_path, 'rb') as f:
                            base64_img = base64.b64encode(f.read()).decode()
                            img['src'] = f"data:image/jpeg;base64,{base64_img}"
                        nova_console.warning(
                            f"Failed to optimize image {idx}/{len(images)}, using original: {str(e)}"
                        )
                    except Exception as e2:
                        nova_console.warning(
                            f"Failed to process image {idx}/{len(images)}: {str(e2)}"
                        )
                    
            except Exception as e:
                nova_console.warning(f"Failed to process image {idx}/{len(images)}: {str(e)}")
                continue
        
        total_time = time.time() - start_time
        nova_console.process_item(
            f"Image optimization complete: {len(images)} images in {total_time:.2f}s "
            f"(avg {total_time/len(images):.2f}s per image)"
        )
                
        return str(soup)

def main():
    """CLI entry point."""
    if len(sys.argv) < 3:
        nova_console.error("Usage: python markdown_to_pdf_converter.py <input_file> <output_file>")
        sys.exit(1)
        
    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    
    if not input_file.exists():
        nova_console.error(f"Input file not found: {input_file}")
        sys.exit(1)
        
    converter = PDFConverter()
    success = converter.convert(input_file, output_file)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()