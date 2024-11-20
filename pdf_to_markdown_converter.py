#!/usr/bin/env python3

import os
import sys
import hashlib
import logging
from pathlib import Path
from typing import Optional, Tuple
import io
import shutil

import click
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from rich.progress import Progress, SpinnerColumn, TextColumn
from bs4 import BeautifulSoup

from colors import Colors, console

# Logging Configuration
logging.basicConfig(
    filename='pdf_converter.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class PDFConverter:
    def __init__(self, input_path: Path, output_path: Path, media_dir: Optional[Path] = None, verbose: bool = False):
        self.input_path = input_path
        self.output_path = output_path
        self.media_dir = media_dir or output_path.parent / '_media'
        self.verbose = verbose
        self.logger = self.setup_logging()
        self.markdown_content = []
        
    def setup_logging(self) -> logging.Logger:
        """Configure logging based on verbosity level."""
        logger = logging.getLogger(__name__)
        if self.verbose:
            logger.setLevel(logging.DEBUG)
        return logger
    
    def save_image(self, image_data: bytes, original_format: str = 'JPEG') -> Optional[Path]:
        """Save and optimize image to media directory."""
        try:
            # Generate hash for image data
            image_hash = hashlib.sha256(image_data).hexdigest()[:8]
            
            # Convert to PIL Image for optimization
            image = Image.open(io.BytesIO(image_data))
            
            # Convert RGBA to RGB if necessary
            if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])
                image = background
            
            # Resize if too large (max dimension 1200px)
            max_size = 1200
            if max(image.size) > max_size:
                ratio = max_size / max(image.size)
                new_size = tuple(int(dim * ratio) for dim in image.size)
                image = image.resize(new_size, Image.LANCZOS)
            
            # Create media directory if it doesn't exist
            self.media_dir.mkdir(parents=True, exist_ok=True)
            
            # Save image with hash in filename
            image_path = self.media_dir / f"image_{image_hash}.jpg"
            image.save(image_path, format='JPEG', quality=85, optimize=True)
            
            return image_path
            
        except Exception as e:
            self.logger.error(f"Error saving image: {e}")
            return None

    def extract_text_from_image(self, image_data: bytes) -> str:
        """Extract text from image using OCR."""
        try:
            image = Image.open(io.BytesIO(image_data))
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            self.logger.error(f"OCR error: {e}")
            return ""

    def process_page(self, page) -> str:
        """Process a single PDF page."""
        content = []
        
        # Extract text blocks
        blocks = page.get_text("blocks")
        for block in blocks:
            text = block[4].strip()
            if text:
                content.append(text + "\n\n")
        
        # Extract images
        image_list = page.get_images(full=True)
        for img_index, img_info in enumerate(image_list):
            try:
                base_image = self.doc.extract_image(img_info[0])
                if base_image:
                    image_data = base_image["image"]
                    
                    # Try OCR on the image
                    ocr_text = self.extract_text_from_image(image_data)
                    if ocr_text:
                        content.append(f"\n{ocr_text}\n\n")
                    
                    # Save image and get relative path
                    image_path = self.save_image(image_data)
                    if image_path:
                        # Calculate relative path from markdown file to image
                        rel_path = os.path.relpath(image_path, self.output_path.parent)
                        content.append(f"\n![Image {img_index + 1}]({rel_path})\n\n")
                    
            except Exception as e:
                self.logger.error(f"Error processing image: {e}")
        
        return "".join(content)

    def convert(self) -> bool:
        """Convert PDF to Markdown."""
        try:
            Colors.info(f"Converting PDF: {self.input_path}")
            self.doc = fitz.open(self.input_path)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Converting PDF...", total=len(self.doc))
                
                for page_num in range(len(self.doc)):
                    page = self.doc[page_num]
                    content = self.process_page(page)
                    self.markdown_content.append(content)
                    progress.update(task, advance=1)
            
            # Write the markdown content
            markdown_text = "\n".join(self.markdown_content)
            self.output_path.write_text(markdown_text, encoding='utf-8')
            
            Colors.success(f"Conversion complete: {self.output_path}")
            self.logger.info(f"Successfully converted {self.input_path} to {self.output_path}")
            return True
            
        except Exception as e:
            Colors.error(f"Conversion failed: {e}")
            self.logger.error(f"Conversion failed: {e}")
            return False
        finally:
            if hasattr(self, 'doc'):
                self.doc.close()

@click.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path(), required=False)
@click.option('--media-dir', type=click.Path(), help='Directory to store media files')
@click.option('--verbose', is_flag=True, help='Increase output verbosity')
def main(input_file: str, output_file: Optional[str], media_dir: Optional[str], verbose: bool):
    """Convert PDF to Markdown with linked images."""
    try:
        input_path = Path(input_file)
        output_path = Path(output_file) if output_file else input_path.with_suffix('.md')
        media_dir_path = Path(media_dir) if media_dir else output_path.parent / '_media'
        
        converter = PDFConverter(input_path, output_path, media_dir_path, verbose)
        success = converter.convert()
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        Colors.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 