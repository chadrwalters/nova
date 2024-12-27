"""Image converter for processing image files."""

import os
import time
import json
import shutil
import magic
import logging
import aiofiles
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from PIL import Image, ExifTags
import tempfile
import subprocess
import io

from .....core.logging import get_logger
from .....core.providers.grok_provider import GrokProvider
from .....core.file_info_provider import FileInfoProvider

logger = get_logger(__name__)

@dataclass
class ImageInfo:
    """Information about a processed image."""
    success: bool
    content_type: str
    metadata: Dict[str, Any]
    description: str
    visible_text: str
    context: Dict[str, Any]
    timings: Dict[str, Any]
    error: Optional[str] = None

@dataclass
class ImageConversionResult:
    """Result of image conversion and analysis."""
    content: bytes
    format: str
    dimensions: Tuple[int, int]
    metadata: Dict[str, Any]
    source_path: Path
    output_path: Optional[Path]
    timings: Dict[str, Union[float, str]]
    success: bool
    error: Optional[str] = None
    content_type: str = "image"  # image, screenshot, diagram, document
    description: Optional[str] = None  # General description or analysis
    visible_text: Optional[str] = None  # Extracted text content if present
    context: Optional[Dict[str, str]] = None  # Additional structured context

class ImageConverter:
    """Handles image conversion and analysis."""
    
    SUPPORTED_FORMATS = {
        'JPEG', 'JPG', 'PNG', 'GIF', 'WEBP', 'HEIC', 'HEIF',
        'BMP', 'TIFF', 'TIF'
    }
    
    def __init__(self, analyze_images: bool = False):
        """Initialize image converter.
        
        Args:
            analyze_images: Whether to analyze images with XAI Vision API
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Initialize file info provider
        self.file_info_provider = FileInfoProvider()
        
        # Check for ImageMagick installation
        try:
            subprocess.run(['magick', '--version'], capture_output=True, check=True)
            self.has_imagemagick = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.has_imagemagick = False
            self.logger.warning("ImageMagick not found. HEIC conversion will be disabled.")
        
        # Initialize Grok provider if API key is available and analysis is enabled
        self.grok_provider = None
        self.analyze_images = analyze_images
        if analyze_images and os.environ.get('XAI_API_KEY'):
            self.grok_provider = GrokProvider(
                api_key=os.environ.get('XAI_API_KEY'),
                cache_dir=os.environ.get('XAI_CACHE_DIR')
            )
        elif analyze_images:
            self.logger.warning("XAI_API_KEY not found. Image analysis will be disabled.")
    
    def is_supported_image(self, file_path: Path) -> bool:
        """Check if the file is a supported image format.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            bool: True if supported, False otherwise
        """
        # Check file extension first
        ext = file_path.suffix.lstrip('.').upper()
        if ext in ['HEIC', 'HEIF']:
            return self.has_imagemagick
            
        try:
            # Try to open with PIL
            with Image.open(file_path) as img:
                return img.format.upper() in self.SUPPORTED_FORMATS
        except Exception:
            # If PIL fails, check file extension
            return ext in self.SUPPORTED_FORMATS
    
    def _parse_grok_response(self, response: str) -> Tuple[str, str, Optional[str], Optional[dict]]:
        """Parse the structured response from Grok into components.
        
        Args:
            response: Raw response from Grok API
            
        Returns:
            Tuple of (content_type, description, visible_text, context)
        """
        # Default values
        content_type = "image"
        description = response
        visible_text = None
        context = None
        
        # Check if it's a screenshot based on keywords
        screenshot_keywords = [
            'screenshot', 'ui', 'interface', 'window', 'dialog', 'menu',
            'button', 'text field', 'toolbar', 'desktop'
        ]
        
        is_screenshot = any(keyword in response.lower() for keyword in screenshot_keywords)
        
        if is_screenshot:
            content_type = "screenshot"
            
            # Try to extract structured information
            try:
                # Split visible text from description
                text_markers = [
                    "Visible text:", "Text content:", "Text shown:", 
                    "Text displayed:", "Contains text:"
                ]
                
                for marker in text_markers:
                    if marker in response:
                        parts = response.split(marker, 1)
                        if len(parts) == 2:
                            description = parts[0].strip()
                            visible_text = parts[1].strip()
                            break
                
                # Extract UI context if present
                context_markers = [
                    "UI elements:", "Layout:", "Interface elements:",
                    "Screen elements:", "Components:"
                ]
                
                for marker in context_markers:
                    if marker in description:
                        desc_parts = description.split(marker, 1)
                        if len(desc_parts) == 2:
                            description = desc_parts[0].strip()
                            context = {
                                "ui_elements": desc_parts[1].strip()
                            }
                            break
                            
            except Exception as e:
                self.logger.warning(f"Failed to parse structured response: {str(e)}")
                # Fall back to raw response
                description = response
                visible_text = None
                context = None
        
        return content_type, description, visible_text, context
    
    async def convert_image(self, image_path: Path) -> ImageInfo:
        """Convert an image file and return its metadata."""
        try:
            # Check if file is a supported image
            if not self.is_supported_image(image_path):
                raise ValueError(f"Unsupported image format: {image_path}")
            
            # Handle HEIC/HEIF files
            if image_path.suffix.lower() in ['.heic', '.heif']:
                if not self.has_imagemagick:
                    raise ValueError("ImageMagick not available for HEIC conversion")
                    
                # Create temporary JPEG file
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                    temp_jpg = Path(tmp_file.name)
                
                try:
                    # Convert HEIC to JPEG
                    subprocess.run(['magick', str(image_path), str(temp_jpg)], check=True)
                    
                    # Now process the converted JPEG
                    with Image.open(temp_jpg) as img:
                        metadata = {
                            'original_format': 'HEIC',
                            'target_format': 'JPEG',
                            'content_type': 'image/jpeg',
                            'width': img.width,
                            'height': img.height,
                            'mode': img.mode,
                            'size': os.path.getsize(image_path),
                            'modified': datetime.fromtimestamp(os.path.getmtime(image_path))
                        }
                finally:
                    # Clean up temporary file
                    if temp_jpg.exists():
                        temp_jpg.unlink()
            else:
                # Process non-HEIC images directly with PIL
                with Image.open(image_path) as img:
                    metadata = {
                        'original_format': img.format or 'UNKNOWN',
                        'target_format': 'JPEG',
                        'content_type': f'image/{img.format.lower() if img.format else "jpeg"}',
                        'width': img.width,
                        'height': img.height,
                        'mode': img.mode,
                        'size': os.path.getsize(image_path),
                        'modified': datetime.fromtimestamp(os.path.getmtime(image_path))
                    }

                    # Add EXIF data if available
                    if hasattr(img, '_getexif') and img._getexif() is not None:
                        exif = {
                            ExifTags.TAGS[k]: str(v)
                            for k, v in img._getexif().items()
                            if k in ExifTags.TAGS
                        }
                        metadata['exif'] = exif

            return ImageInfo(
                success=True,
                content_type=metadata['content_type'],
                metadata=metadata,
                description="Image processed successfully",
                visible_text=None,
                context=None,
                timings={},
                error=None
            )

        except Exception as e:
            self.logger.error(f"Error converting image {image_path}: {str(e)}")
            return ImageInfo(
                success=False,
                content_type='image',
                metadata={},
                description=None,
                visible_text=None,
                context=None,
                timings={},
                error=str(e)
            )
    
    async def get_image_info(self, file_path: Path, output_path: Path) -> ImageInfo:
        """Get information about an image file.
        
        Args:
            file_path: Path to the image file
            output_path: Path to save processed image
            
        Returns:
            ImageInfo containing image metadata and processing results
        """
        try:
            # Check if file is a supported image
            if not self.is_supported_image(file_path):
                raise ValueError(f"Unsupported image format: {file_path}")
            
            # Get file info
            file_info = await self.file_info_provider.get_file_info(file_path)
            
            # Create output directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Handle HEIC/HEIF files
            if file_path.suffix.lower() in ['.heic', '.heif']:
                if not self.has_imagemagick:
                    raise ValueError("ImageMagick not available for HEIC conversion")
                    
                # Convert HEIC to JPEG using ImageMagick
                try:
                    # Ensure output has .jpg extension
                    output_path = output_path.with_suffix('.jpg')
                    subprocess.run(['magick', str(file_path), str(output_path)], check=True)
                    
                    # Get metadata from converted file
                    with Image.open(output_path) as img:
                        metadata = {
                            'original_format': 'HEIC',
                            'target_format': 'JPEG',
                            'content_type': 'image/jpeg',
                            'size': os.path.getsize(file_path),
                            'modified': datetime.fromtimestamp(os.path.getmtime(file_path)),
                            'dimensions': img.size
                        }
                except subprocess.CalledProcessError as e:
                    raise ValueError(f"Failed to convert HEIC to JPEG: {str(e)}")
            else:
                # For non-HEIC images, get metadata first
                with Image.open(file_path) as img:
                    metadata = {
                        'original_format': img.format or file_path.suffix.lstrip('.').upper(),
                        'target_format': img.format or 'JPEG',
                        'content_type': getattr(file_info, 'content_type', f'image/{img.format.lower() if img.format else "jpeg"}'),
                        'size': os.path.getsize(file_path),
                        'modified': datetime.fromtimestamp(os.path.getmtime(file_path)),
                        'dimensions': img.size
                    }
                    
                    # Add EXIF data if available
                    if hasattr(img, '_getexif') and img._getexif() is not None:
                        exif = {
                            ExifTags.TAGS[k]: str(v)
                            for k, v in img._getexif().items()
                            if k in ExifTags.TAGS
                        }
                        metadata['exif'] = exif
                
                # Copy file to output location using binary mode
                with open(file_path, 'rb') as src, open(output_path, 'wb') as dst:
                    dst.write(src.read())
            
            # Save metadata to JSON file
            metadata_file = output_path.with_suffix('.json')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            return ImageInfo(
                success=True,
                content_type=metadata['content_type'],
                metadata=metadata,
                description=None,
                visible_text=None,
                context=None,
                timings={},
                error=None
            )
            
        except Exception as e:
            return ImageInfo(
                success=False,
                content_type=None,
                metadata={},
                description=None,
                visible_text=None,
                context=None,
                timings={},
                error=str(e)
            )
    
    async def process(self, image_path: Path, output_dir: Path) -> ImageInfo:
        """Process an image file.
        
        Args:
            image_path: Path to the image file
            output_dir: Directory to save processed files
            
        Returns:
            ImageInfo containing processing results
        """
        try:
            # Check if file is a supported image
            if not self.is_supported_image(image_path):
                raise ValueError(f"Unsupported image format: {image_path}")
            
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Define output paths
            if image_path.suffix.lower() in ['.heic', '.heif']:
                output_path = output_dir / f"{image_path.stem}.jpg"
            else:
                output_path = output_dir / image_path.name
            
            # Convert and get info
            info = await self.convert_image(image_path)
            if not info.success:
                return info
            
            # Process the image and save to output location
            result = await self.get_image_info(image_path, output_path)
            if not result.success:
                return result
            
            # Update metadata with processing info
            metadata = result.metadata
            metadata.update({
                'processing': {
                    'timestamp': datetime.now().isoformat(),
                    'original_path': str(image_path),
                    'output_path': str(output_path),
                    'success': True
                }
            })
            
            # Save metadata to JSON file
            metadata_file = output_path.with_suffix('.json')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            return ImageInfo(
                success=True,
                content_type=metadata['content_type'],
                metadata=metadata,
                description="Image processed successfully",
                visible_text=None,
                context=None,
                timings={},
                error=None
            )
            
        except Exception as e:
            self.logger.error(f"Failed to process image {image_path}: {str(e)}")
            return ImageInfo(
                success=False,
                content_type=None,
                metadata={},
                description=None,
                visible_text=None,
                context=None,
                timings={},
                error=str(e)
            ) 