"""Handler for processing and optimizing images."""

import os
from pathlib import Path
from typing import Dict, Any, Optional, Set
import aiofiles
import aiohttp
from PIL import Image
import piexif

from ..base_handler import BaseHandler
from ...config.defaults import DEFAULT_CONFIG

class ImageHandler(BaseHandler):
    """Handles processing and optimization of images."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the image handler.
        
        Args:
            config: Optional configuration overrides
        """
        super().__init__(config)
        self.supported_formats = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.heic', '.HEIC'}
        
        # Merge default config with provided config
        self.config = {**DEFAULT_CONFIG.get('image', {}), **(config or {})}
        
        # Set up paths
        self.original_dir = Path(os.getenv('NOVA_ORIGINAL_IMAGES_DIR', ''))
        self.processed_dir = Path(os.getenv('NOVA_PROCESSED_IMAGES_DIR', ''))
        self.metadata_dir = Path(os.getenv('NOVA_IMAGE_METADATA_DIR', ''))
        self.cache_dir = Path(os.getenv('NOVA_IMAGE_CACHE_DIR', ''))
    
    def can_handle(self, file_path: Path) -> bool:
        """Check if file is a supported image.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            bool: True if file is a supported image format
        """
        return file_path.suffix.lower() in self.supported_formats
    
    async def process(self, file_path: Path, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process an image file.
        
        Args:
            file_path: Path to the image file
            context: Processing context
            
        Returns:
            Dict containing:
                - processed_path: Path to processed image
                - original_path: Path to original image
                - metadata: Extracted metadata
                - format: Image format
                - dimensions: Image dimensions
                - size: File size
                - errors: List of processing errors
        """
        result = {
            'processed_path': '',
            'original_path': '',
            'metadata': {},
            'format': '',
            'dimensions': (0, 0),
            'size': 0,
            'errors': []
        }
        
        try:
            # Copy original to storage
            original_path = await self._store_original(file_path)
            result['original_path'] = str(original_path)
            
            # Process image
            processed_path = await self._process_image(file_path)
            result['processed_path'] = str(processed_path)
            
            # Extract metadata
            result['metadata'] = await self._extract_metadata(file_path)
            
            # Get image info
            with Image.open(processed_path) as img:
                result['format'] = img.format.lower()
                result['dimensions'] = img.size
            
            result['size'] = processed_path.stat().st_size
            
        except Exception as e:
            result['errors'].append(str(e))
        
        return result
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate processing results.
        
        Args:
            result: Processing results to validate
            
        Returns:
            bool: True if results are valid
        """
        required_keys = {
            'processed_path', 'original_path', 'metadata',
            'format', 'dimensions', 'size', 'errors'
        }
        return (
            all(key in result for key in required_keys) and
            isinstance(result['processed_path'], str) and
            isinstance(result['original_path'], str) and
            isinstance(result['metadata'], dict) and
            isinstance(result['format'], str) and
            isinstance(result['dimensions'], tuple) and
            isinstance(result['size'], int) and
            isinstance(result['errors'], list)
        )
    
    async def _store_original(self, file_path: Path) -> Path:
        """Store original image."""
        target_path = self.original_dir / file_path.name
        async with aiofiles.open(file_path, 'rb') as src, \
                   aiofiles.open(target_path, 'wb') as dst:
            await dst.write(await src.read())
        return target_path
    
    async def _process_image(self, file_path: Path) -> Path:
        """Process and optimize image."""
        target_path = self.processed_dir / f"{file_path.stem}.jpg"
        
        with Image.open(file_path) as img:
            # Convert HEIC to JPEG if needed
            if file_path.suffix.lower() in {'.heic', '.HEIC'}:
                img = img.convert('RGB')
            
            # Resize if needed
            max_dims = self.config.get('max_dimensions', (1920, 1080))
            if img.size[0] > max_dims[0] or img.size[1] > max_dims[1]:
                img.thumbnail(max_dims, Image.LANCZOS)
            
            # Save with optimization
            img.save(
                target_path,
                'JPEG',
                quality=self.config.get('jpeg_quality', 85),
                optimize=True
            )
        
        return target_path
    
    async def _extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract image metadata."""
        metadata = {}
        
        try:
            with Image.open(file_path) as img:
                # Basic metadata
                metadata.update({
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                })
                
                # EXIF data if available
                if 'exif' in img.info:
                    exif_dict = piexif.load(img.info['exif'])
                    metadata['exif'] = {
                        IFD: {
                            piexif.TAGS[IFD][tag]['name']: value
                            for tag, value in tags.items()
                        }
                        for IFD, tags in exif_dict.items()
                        if isinstance(tags, dict)
                    }
        except Exception as e:
            metadata['extraction_error'] = str(e)
        
        return metadata 