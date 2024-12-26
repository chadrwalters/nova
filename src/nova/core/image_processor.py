"""Image processing module."""

import os
import time
import base64
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from PIL import Image, ExifTags
import tempfile
import subprocess
import io

from nova.core.logging import get_logger
from nova.core.providers.grok_provider import GrokProvider

logger = get_logger(__name__)

class ImageProcessingError(Exception):
    """Base class for image processing errors."""
    pass

class ImageNotFoundError(ImageProcessingError):
    """Raised when an image file is not found."""
    pass

class InvalidImageFormatError(ImageProcessingError):
    """Raised when an image format is not supported."""
    pass

@dataclass
class ImageConversionResult:
    """Result of image conversion."""
    content: bytes
    format: str
    dimensions: Tuple[int, int]
    metadata: Dict[str, Any]
    description: Optional[str] = None
    extracted_text: Optional[str] = None
    is_screenshot: bool = False
    timings: Dict[str, float] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None

class ImageProcessor:
    """Handles image processing operations."""
    
    def __init__(self):
        """Initialize image processor."""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Initialize Grok provider if API key is available
        self.grok_provider = None
        if os.environ.get('XAI_API_KEY'):
            self.grok_provider = GrokProvider(
                api_key=os.environ.get('XAI_API_KEY'),
                cache_dir=os.environ.get('XAI_CACHE_DIR')
            )
        else:
            self.logger.warning("XAI_API_KEY not found. Image description and text extraction will be disabled.")
    
    async def convert_image(self, file_path: Path) -> ImageConversionResult:
        """Convert HEIC/HEIF image to JPEG format."""
        start_time = time.time()
        temp_path = None
        timings = {}
        
        try:
            # Create temp file for conversion
            temp_start = time.time()
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_path = Path(temp_file.name)
            timings['temp_creation'] = time.time() - temp_start
            
            # Convert using sips command
            convert_start = time.time()
            cmd = ['sips', '-s', 'format', 'jpeg', str(file_path), '--out', str(temp_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            timings['conversion'] = time.time() - convert_start
            
            if result.returncode != 0:
                return ImageConversionResult(
                    content=b'',
                    format='',
                    dimensions=(0, 0),
                    metadata={},
                    timings=timings,
                    success=False,
                    error=f"Conversion failed: {result.stderr}"
                )
            
            # Read converted image and get metadata
            read_start = time.time()
            with Image.open(temp_path) as img:
                # Get dimensions
                dimensions = img.size
                
                # Extract EXIF metadata
                metadata = {}
                try:
                    exif = {
                        ExifTags.TAGS[k]: str(v)
                        for k, v in img._getexif().items()
                        if k in ExifTags.TAGS
                    } if img._getexif() else {}
                    metadata['exif'] = exif
                except Exception as e:
                    self.logger.warning(f"Failed to extract EXIF data: {str(e)}")
                
                # Convert to bytes
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG')
                content = img_byte_arr.getvalue()
            timings['read_and_metadata'] = time.time() - read_start
            
            # Get description and text extraction using Grok
            description = None
            extracted_text = None
            is_screenshot = False
            
            if self.grok_provider:
                try:
                    # Get image description and analysis
                    desc_start = time.time()
                    grok_result = await self.grok_provider.get_image_description(str(temp_path))
                    timings['grok_analysis'] = time.time() - desc_start
                    
                    if grok_result:
                        # Handle string response from Grok
                        if isinstance(grok_result, str):
                            description = grok_result
                            is_screenshot = "screenshot" in grok_result.lower() or "ui" in grok_result.lower()
                            # If it's a screenshot, the text is already in the description
                            if is_screenshot:
                                extracted_text = grok_result
                        elif isinstance(grok_result, dict):
                            description = grok_result.get('description')
                            extracted_text = grok_result.get('text')
                            is_screenshot = "screenshot" in description.lower() or "ui" in description.lower()
                except Exception as e:
                    self.logger.warning(f"Failed to analyze image: {str(e)}")
                    timings['grok_error'] = str(e)
            
            timings['total'] = time.time() - start_time
            
            result = ImageConversionResult(
                content=content,
                format='jpeg',
                dimensions=dimensions,
                metadata=metadata,
                description=description,
                extracted_text=extracted_text,
                is_screenshot=is_screenshot,
                timings=timings,
                success=True
            )
            
            # Clean up temp file
            if temp_path and temp_path.exists():
                temp_path.unlink()
            
            return result
            
        except Exception as e:
            # Clean up temp file if we created one
            if temp_path and temp_path.exists():
                temp_path.unlink()
            
            timings['total'] = time.time() - start_time
            timings['error'] = str(e)
            
            return ImageConversionResult(
                content=b'',
                format='',
                dimensions=(0, 0),
                metadata={},
                timings=timings,
                success=False,
                error=str(e)
            )
    
    async def get_image_info(self, file_path: Path) -> ImageConversionResult:
        """Get image information and generate description."""
        start_time = time.time()
        temp_path = None
        timings = {}
        
        try:
            # Handle HEIC files first
            if file_path.suffix.lower() in ['.heic', '.heif']:
                # Convert using sips command
                convert_start = time.time()
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                    temp_path = Path(temp_file.name)
                cmd = ['sips', '-s', 'format', 'jpeg', str(file_path), '--out', str(temp_path)]
                result = subprocess.run(cmd, capture_output=True, text=True)
                timings['heic_conversion'] = time.time() - convert_start
                
                if result.returncode != 0:
                    raise Exception(f"HEIC conversion failed: {result.stderr}")
                file_path = temp_path

            # Open image and get basic info
            read_start = time.time()
            with Image.open(file_path) as img:
                # Get dimensions
                dimensions = img.size
                
                # Extract EXIF metadata
                metadata = {}
                try:
                    exif = {
                        ExifTags.TAGS[k]: str(v)
                        for k, v in img._getexif().items()
                        if k in ExifTags.TAGS
                    } if img._getexif() else {}
                    metadata['exif'] = exif
                except Exception as e:
                    self.logger.warning(f"Failed to extract EXIF data: {str(e)}")
            timings['read_and_metadata'] = time.time() - read_start
            
            # Get description and text extraction using Grok
            description = None
            extracted_text = None
            is_screenshot = False
            
            if self.grok_provider:
                try:
                    # Get image description and analysis
                    desc_start = time.time()
                    grok_result = await self.grok_provider.get_image_description(str(file_path))
                    timings['grok_analysis'] = time.time() - desc_start
                    
                    if grok_result:
                        # Handle string response from Grok
                        if isinstance(grok_result, str):
                            description = grok_result
                            is_screenshot = "screenshot" in grok_result.lower() or "ui" in grok_result.lower()
                            # If it's a screenshot, the text is already in the description
                            if is_screenshot:
                                extracted_text = grok_result
                        elif isinstance(grok_result, dict):
                            description = grok_result.get('description')
                            extracted_text = grok_result.get('text')
                            is_screenshot = "screenshot" in description.lower() or "ui" in description.lower()
                except Exception as e:
                    self.logger.warning(f"Failed to analyze image: {str(e)}")
                    timings['grok_error'] = str(e)
            
            timings['total'] = time.time() - start_time
            
            result = ImageConversionResult(
                content=b'',  # Not needed for info
                format=img.format.lower(),
                dimensions=dimensions,
                metadata=metadata,
                description=description,
                extracted_text=extracted_text,
                is_screenshot=is_screenshot,
                timings=timings,
                success=True
            )
            
            # Clean up temp file if we created one
            if temp_path and temp_path.exists():
                temp_path.unlink()
            
            return result
                
        except Exception as e:
            # Clean up temp file if we created one
            if temp_path and temp_path.exists():
                temp_path.unlink()
            
            timings['total'] = time.time() - start_time
            timings['error'] = str(e)
            
            return ImageConversionResult(
                content=b'',
                format='',
                dimensions=(0, 0),
                metadata={},
                timings=timings,
                success=False,
                error=str(e)
            ) 