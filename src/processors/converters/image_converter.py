from PIL import Image, ExifTags
from pathlib import Path
from typing import Dict, Any, Optional
import structlog
from datetime import datetime

from src.processors.converters.base_converter import BaseConverter
from src.core.exceptions import ConversionError

logger = structlog.get_logger(__name__)

class ImageConverter(BaseConverter):
    """Handles image files."""
    
    async def convert(self, file_path: Path) -> Optional[Path]:
        """Convert image to web-friendly format if needed."""
        try:
            # Handle HEIC images
            if file_path.suffix.lower() == '.heic':
                try:
                    with Image.open(file_path) as img:
                        # Convert to JPEG
                        output_path = file_path.with_suffix('.jpg')
                        img.save(output_path, 'JPEG')
                        return output_path
                except Exception as e:
                    logger.error(f"Failed to convert HEIC image: {e}")
                    return None
                    
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to convert image: {e}")
            return None
    
    async def get_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Get image metadata.
        
        Args:
            file_path: Path to image file
            
        Returns:
            Dictionary of metadata
        """
        try:
            with Image.open(file_path) as img:
                metadata = {
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'width': img.size[0],
                    'height': img.size[1],
                    'file_size': file_path.stat().st_size,
                    'created': datetime.fromtimestamp(file_path.stat().st_ctime),
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime)
                }
                
                # Try to get EXIF data if available
                try:
                    exif = img.getexif()
                    if exif:
                        # Convert EXIF tags to human-readable form
                        exif_data = {}
                        for tag_id in exif:
                            try:
                                tag = ExifTags.TAGS.get(tag_id, tag_id)
                                value = exif.get(tag_id)
                                if isinstance(value, bytes):
                                    value = value.decode(errors='ignore')
                                exif_data[tag] = value
                            except Exception:
                                continue
                        
                        # Add selected EXIF data to metadata
                        important_tags = {
                            'Make', 'Model', 'DateTime', 
                            'ExposureTime', 'FNumber', 'ISOSpeedRatings'
                        }
                        metadata['exif'] = {
                            k: v for k, v in exif_data.items() 
                            if k in important_tags
                        }
                except Exception:
                    pass
                
                return metadata
                
        except Exception as e:
            logger.warning(
                "Failed to get image metadata",
                error=str(e),
                file=str(file_path)
            )
            return {} 