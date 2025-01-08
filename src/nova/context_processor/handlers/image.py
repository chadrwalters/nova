"""Image file handler."""

import logging
import os
from pathlib import Path
from typing import Optional, Tuple
import base64

from PIL import Image, UnidentifiedImageError
from pillow_heif import register_heif_opener
import cairosvg
import io

from nova.context_processor.config.manager import ConfigManager
from nova.context_processor.core.metadata.models.types import ImageMetadata
from nova.context_processor.handlers.base import BaseHandler
from nova.context_processor.utils.file_utils import calculate_file_hash

logger = logging.getLogger(__name__)

# Register HEIF/HEIC support
register_heif_opener()


class ImageHandler(BaseHandler):
    """Handler for image files."""

    def __init__(self, config: ConfigManager):
        """Initialize handler.

        Args:
            config: Configuration manager
        """
        super().__init__(config)
        self.supported_extensions = {
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", 
            ".tiff", ".webp", ".heic", ".heif", ".svg"
        }

    async def _convert_to_jpeg(self, file_path: Path) -> Tuple[Optional[bytes], Optional[dict]]:
        """Convert image to JPEG format.

        Args:
            file_path: Path to input file

        Returns:
            Tuple of (JPEG bytes, image info)
        """
        image_info = {}

        try:
            if file_path.suffix.lower() == '.svg':
                # Convert SVG to PNG first, then to JPEG
                png_data = cairosvg.svg2png(url=str(file_path))
                img = Image.open(io.BytesIO(png_data))
            else:
                img = Image.open(file_path)

            # Extract image info
            image_info = {
                'width': img.width,
                'height': img.height,
                'mode': img.mode,
                'format': img.format,
                'has_alpha': img.mode.endswith('A'),
            }
            
            try:
                image_info['dpi'] = img.info.get('dpi')
            except Exception:
                pass

            # Convert to RGB if needed
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[3])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Save as JPEG to bytes
            jpeg_bytes = io.BytesIO()
            img.save(jpeg_bytes, format='JPEG', quality=95)
            return jpeg_bytes.getvalue(), image_info

        except Exception as e:
            logger.error(f"Failed to convert image {file_path}: {str(e)}")
            return None, None

    async def _process_file(self, file_path: Path, metadata: ImageMetadata) -> bool:
        """Process an image file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether processing was successful
        """
        try:
            # Convert image and get info
            jpeg_bytes, image_info = await self._convert_to_jpeg(file_path)
            if not jpeg_bytes or not image_info:
                return False

            # Update metadata
            metadata.width = image_info['width']
            metadata.height = image_info['height']
            metadata.format = image_info['format']
            metadata.color_space = image_info['mode']
            metadata.has_alpha = image_info['has_alpha']
            if 'dpi' in image_info:
                metadata.dpi = image_info['dpi']

            return True

        except Exception as e:
            logger.error(f"Failed to process image {file_path}: {e}")
            return False

    async def _parse_file(self, file_path: Path, metadata: ImageMetadata) -> bool:
        """Parse an image file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether parsing was successful
        """
        try:
            # Convert image and get info
            jpeg_bytes, image_info = await self._convert_to_jpeg(file_path)
            if not jpeg_bytes or not image_info:
                return False

            # Update metadata
            metadata.width = image_info['width']
            metadata.height = image_info['height']
            metadata.format = image_info['format']
            metadata.color_space = image_info['mode']
            metadata.has_alpha = image_info['has_alpha']
            if 'dpi' in image_info:
                metadata.dpi = image_info['dpi']

            return True

        except Exception as e:
            logger.error(f"Failed to parse image {file_path}: {e}")
            return False

    async def _disassemble_file(self, file_path: Path, metadata: ImageMetadata) -> bool:
        """Disassemble an image file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether disassembly was successful
        """
        try:
            # For now, just copy the file
            metadata.file_size = file_path.stat().st_size
            metadata.file_hash = calculate_file_hash(file_path)

            return True

        except Exception as e:
            logger.error(f"Failed to disassemble image {file_path}: {e}")
            return False

    async def _split_file(self, file_path: Path, metadata: ImageMetadata) -> bool:
        """Split an image file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether splitting was successful
        """
        try:
            # For now, just copy the file
            metadata.file_size = file_path.stat().st_size
            metadata.file_hash = calculate_file_hash(file_path)

            return True

        except Exception as e:
            logger.error(f"Failed to split image {file_path}: {e}")
            return False
