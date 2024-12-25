"""Image handling components for Nova processors."""

from pathlib import Path
from typing import Dict, Any, Optional, List
import shutil
from PIL import Image

from .base import BaseHandler
from ..errors import ProcessingError, ImageProcessingError
from ..image_processor import ImageProcessor

class ImageHandler(BaseHandler):
    """Handles image processing and optimization."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize image handler.
        
        Args:
            config: Handler configuration
        """
        super().__init__(config)
        self.config = config or {}
        
        # Initialize image processor (will be properly initialized in setup)
        self.processor = None
    
    async def _setup(self) -> None:
        """Setup handler requirements."""
        await super()._setup()
        
        # Initialize image processor within async context
        self.processor = ImageProcessor(config=self.config)
        self.processor = await self.processor.__aenter__()
    
    async def _cleanup(self) -> None:
        """Clean up handler resources."""
        # Clean up image processor
        if self.processor:
            await self.processor.__aexit__(None, None, None)
        
        await super()._cleanup()
    
    def can_handle(self, file_path: Path) -> bool:
        """Check if file can be handled.
        
        Args:
            file_path: Path to check
            
        Returns:
            bool: True if file is an image type
        """
        if not self.processor:
            return False
        return file_path.suffix.lower() in self.processor.supported_formats
    
    async def process(self, file_path: Path) -> Dict[str, Any]:
        """Process an image file.
        
        Args:
            file_path: Path to image file
            
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