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

from nova.core.logging import get_logger
from nova.core.providers.grok_provider import GrokProvider
from nova.core.file_info_provider import FileInfoProvider

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
    
    def __init__(self, analyze_images: bool = False):
        """Initialize image converter.
        
        Args:
            analyze_images: Whether to analyze images with XAI Vision API
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
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
            # Get image format and metadata
            with Image.open(image_path) as img:
                format = img.format or 'UNKNOWN'
                dimensions = (img.width, img.height)
                metadata = {
                    'original_format': format,
                    'target_format': 'JPEG',
                    'width': img.width,
                    'height': img.height,
                    'mode': img.mode,
                }

                # Add EXIF data if available
                if hasattr(img, '_getexif') and img._getexif() is not None:
                    exif = {
                        ExifTags.TAGS[k]: v
                        for k, v in img._getexif().items()
                        if k in ExifTags.TAGS
                    }
                    metadata['exif'] = exif

            # Add TODO comment for image processing
            description = "//TODO: IMAGE PROCESSING NOT WORKING"

            return ImageInfo(
                success=True,
                content_type='image',
                metadata=metadata,
                description=description,
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
            # Get file info
            file_info = await self.file_info_provider.get_file_info(file_path)
            
            # Get image format from PIL
            with Image.open(file_path) as img:
                original_format = img.format or file_path.suffix.lstrip('.').upper()
                
                # Initialize metadata
                metadata = {
                    'original_format': original_format,
                    'target_format': 'JPEG',
                    'content_type': file_info.content_type,
                    'size': file_info.size,
                    'created': file_info.created,
                    'modified': file_info.modified,
                    'dimensions': img.size
                }
            
            # Copy file to output location
            shutil.copy2(file_path, output_path)
            
            return ImageInfo(
                success=True,
                content_type=file_info.content_type,
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
        """Process an image file and return its metadata."""
        try:
            # Create output directory if it doesn't exist
            output_dir.mkdir(parents=True, exist_ok=True)

            # Get image format and metadata
            with Image.open(image_path) as img:
                format = img.format or 'UNKNOWN'
                metadata = {
                    'original_format': format,
                    'width': img.width,
                    'height': img.height,
                    'mode': img.mode,
                }

                # Add EXIF data if available
                if hasattr(img, '_getexif') and img._getexif() is not None:
                    exif = {
                        ExifTags.TAGS[k]: v
                        for k, v in img._getexif().items()
                        if k in ExifTags.TAGS
                    }
                    metadata['exif'] = exif

            # Copy image to output directory
            output_path = output_dir / image_path.name
            shutil.copy2(image_path, output_path)

            # Add TODO comment for image processing
            description = "//TODO: IMAGE PROCESSING NOT WORKING"

            return ImageInfo(
                success=True,
                content_type='image',
                metadata=metadata,
                description=description,
                visible_text=None,
                context=None,
                timings={},
                error=None
            )

        except Exception as e:
            self.logger.error(f"Error processing image {image_path}: {str(e)}")
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