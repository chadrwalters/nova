"""Handler for processing and optimizing images."""

import os
from pathlib import Path
from typing import Dict, Any, Optional, Set
import aiofiles
from PIL import Image
import piexif

from nova.core.image_processor import ImageProcessor, ImageNotFoundError, InvalidImageFormatError
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
        
        # Initialize image processor (will be properly initialized in setup)
        self.processor = None
    
    async def _setup(self) -> None:
        """Setup handler requirements."""
        await super()._setup()
        
        # Create required directories
        for directory in [self.original_dir, self.processed_dir, self.metadata_dir, self.cache_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize image processor within async context
        self.processor = ImageProcessor(
            cache_dir=self.cache_dir,
            config={
                'optimization': {
                    'jpeg_quality': self.config.get('jpeg_quality', 85)
                }
            }
        )
        self.processor = await self.processor.__aenter__()
    
    async def _cleanup(self) -> None:
        """Clean up handler resources."""
        # Clean up image processor
        if self.processor:
            await self.processor.__aexit__(None, None, None)
        
        await super()._cleanup()
    
    def can_handle(self, file_path: Path) -> bool:
        """Check if file is a supported image.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            bool: True if file is a supported image format
        """
        if not self.processor:
            return False
        return file_path.suffix.lower() in self.supported_formats
    
    async def process(self, file_path: Path) -> Dict[str, Any]:
        """Process an image file.
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            Dict containing processing results
            
        Raises:
            ProcessingError: If processing fails
        """
        try:
            # Setup resources if not already initialized
            if not self.processor:
                await self._setup()
            
            # Process image
            result = await self.processor.process_image(file_path)
            
            return {
                'success': True,
                'file_path': str(file_path),
                'result': result
            }
            
        except Exception as e:
            raise ProcessingError(f"Failed to process image {file_path}: {str(e)}") from e
    
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