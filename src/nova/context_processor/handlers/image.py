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
from nova.context_processor.core.metadata import BaseMetadata
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
            config: Config manager
        """
        super().__init__(config)
        self.temp_dir = Path(config.temp_dir)
        if not self.temp_dir.exists():
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.supported_extensions = {
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", 
            ".tiff", ".webp", ".heic", ".heif", ".svg"
        }

    async def _process_image(self, file_path: Path) -> Optional[Path]:
        """Process an image file.

        Args:
            file_path: Path to image file

        Returns:
            Optional[Path]: Path to processed image if successful, None if failed
        """
        try:
            # Create output file path preserving original extension
            output_file = self.temp_dir / file_path.name

            # Handle SVG files
            if file_path.suffix.lower() == '.svg':
                try:
                    # Convert SVG to PNG using cairosvg
                    png_data = cairosvg.svg2png(url=str(file_path))
                    # Save as PNG
                    output_file = output_file.with_suffix('.png')
                    with open(output_file, 'wb') as f:
                        f.write(png_data)
                    return output_file
                except Exception as e:
                    logger.warning(f"Failed to convert SVG {file_path}, copying as-is: {e}")
                    # Fall back to copying the original SVG
                    with open(file_path, 'rb') as src, open(output_file, 'wb') as dst:
                        dst.write(src.read())
                    return output_file

            # For all other image types, copy the file preserving format
            with open(file_path, 'rb') as src, open(output_file, 'wb') as dst:
                dst.write(src.read())

            return output_file

        except Exception as e:
            logger.error(f"Failed to process image {file_path}: {str(e)}")
            return None

    async def _process_file(self, file_path: Path, metadata: BaseMetadata) -> bool:
        """Process an image file.

        Args:
            file_path: Path to file to process
            metadata: Metadata to update

        Returns:
            bool: Whether processing was successful
        """
        try:
            # Handle SVG files
            if file_path.suffix.lower() == '.svg':
                try:
                    # Convert SVG to PNG using cairosvg
                    png_data = cairosvg.svg2png(url=str(file_path))
                    # Save as PNG
                    output_file = self.temp_dir / file_path.name.replace('.svg', '.png')
                    with open(output_file, 'wb') as f:
                        f.write(png_data)
                except Exception as e:
                    logger.warning(f"Failed to convert SVG {file_path}, copying as-is: {e}")
                    # Fall back to copying the original SVG
                    output_file = self.temp_dir / file_path.name
                    with open(file_path, 'rb') as src, open(output_file, 'wb') as dst:
                        dst.write(src.read())
            else:
                # For all other image types, copy the file preserving format
                output_file = self.temp_dir / file_path.name
                with open(file_path, 'rb') as src, open(output_file, 'wb') as dst:
                    dst.write(src.read())

            metadata.output_files.add(str(output_file))

            # Add image information to content
            try:
                with Image.open(file_path) as img:
                    metadata.content = f"""## Image Information
- **Original File**: {file_path.name}
- **Format**: {img.format}
- **Dimensions**: {img.size[0]}x{img.size[1]}
- **Mode**: {img.mode}
"""
            except Exception as e:
                logger.warning(f"Failed to get image info for {file_path}: {e}")
                metadata.content = f"""## Image Information
- **Original File**: {file_path.name}
- **Format**: {file_path.suffix.lstrip('.')}
"""

            return True

        except Exception as e:
            logger.error(f"Failed to process image {file_path}: {str(e)}")
            return False

    async def parse_file(self, file_path: Path) -> Optional[BaseMetadata]:
        """Parse an image file.

        Args:
            file_path: Path to image file

        Returns:
            Optional[BaseMetadata]: Metadata if successful, None if failed
        """
        try:
            # Create metadata
            metadata = BaseMetadata(
                file_path=str(file_path),
                file_name=file_path.name,
                file_type=file_path.suffix.lstrip('.'),
                file_size=file_path.stat().st_size,
                file_hash=self._calculate_file_hash(file_path),
                created_at=file_path.stat().st_ctime,
                modified_at=file_path.stat().st_mtime,
                output_files=set(),
            )

            # Process image
            output_file = await self._process_image(file_path)
            if output_file:
                metadata.output_files.add(str(output_file))

                # Add image information to content
                try:
                    with Image.open(file_path) as img:
                        metadata.content = f"""## Image Information
- **Original File**: {file_path.name}
- **Format**: {img.format}
- **Dimensions**: {img.size[0]}x{img.size[1]}
- **Mode**: {img.mode}
"""
                        metadata.width = img.size[0]
                        metadata.height = img.size[1]
                        metadata.format = img.format
                        metadata.color_space = img.mode
                        metadata.has_alpha = 'A' in img.mode
                        metadata.dpi = img.info.get('dpi', None)
                except Exception as e:
                    logger.warning(f"Failed to get image info for {file_path}: {e}")
                    metadata.content = f"""## Image Information
- **Original File**: {file_path.name}
- **Format**: {file_path.suffix.lstrip('.')}
"""

            return metadata

        except Exception as e:
            logger.error(f"Failed to parse image file {file_path}: {str(e)}")
            return None

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate file hash.

        Args:
            file_path: Path to file

        Returns:
            str: File hash
        """
        import hashlib
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

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

    async def split_file(self, file_path: Path, metadata: BaseMetadata) -> bool:
        """Split an image file.

        Args:
            file_path: Path to file to split
            metadata: Metadata to update

        Returns:
            bool: Whether splitting was successful
        """
        try:
            # For images, we just copy the file as-is
            output_file = self.temp_dir / file_path.name
            with open(file_path, 'rb') as src, open(output_file, 'wb') as dst:
                dst.write(src.read())

            metadata.output_files.add(str(output_file))
            return True

        except Exception as e:
            logger.error(f"Failed to split image {file_path}: {str(e)}")
            return False
