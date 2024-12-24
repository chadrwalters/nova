"""Image processor module for Nova document processor."""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image
import json

from ..core.base import BaseProcessor
from ..core.config import ProcessorConfig, ImageConfig
from ..core.paths import PathsConfig
from ..core.errors import ProcessingError
from ..core.logging import get_logger

class ImageProcessor(BaseProcessor):
    """Processes and optimizes images."""

    def __init__(self, config: ImageConfig, paths: PathsConfig):
        """Initialize image processor.
        
        Args:
            config: Image processor configuration
            paths: Path configuration
        """
        super().__init__(config, paths)
        self.cache = {}
        self._load_cache()

    def process(self, input_path: Path) -> Dict[str, Any]:
        """Process image file.
        
        Args:
            input_path: Path to image file
            
        Returns:
            Dictionary containing processing results
            
        Raises:
            ProcessingError: If processing fails
        """
        try:
            self._ensure_output_dir()
            output_path = self._get_output_path(input_path)
            
            # Check cache
            if self._is_cached(input_path):
                self._log_progress(f"Using cached version of {input_path}")
                return self._get_cached_result(input_path)
            
            # Process image
            img = Image.open(input_path)
            
            # Extract metadata
            metadata = self._extract_metadata(img, input_path)
            
            # Optimize image
            optimized_img = self._optimize_image(img)
            
            # Save processed image
            output_path.parent.mkdir(parents=True, exist_ok=True)
            optimized_img.save(output_path, quality=85, optimize=True)
            
            # Save metadata
            metadata_path = self._get_metadata_path(input_path)
            self._save_metadata(metadata_path, metadata)
            
            result = {
                'input_path': str(input_path),
                'output_path': str(output_path),
                'metadata_path': str(metadata_path),
                'metadata': metadata,
                'status': 'success'
            }
            
            # Update cache
            self._cache_result(input_path, result)
            
            return result
            
        except Exception as e:
            context = {'input_path': str(input_path)}
            self._handle_error(e, context)

    def _extract_metadata(self, img: Image.Image, file_path: Path) -> Dict[str, Any]:
        """Extract image metadata.
        
        Args:
            img: PIL Image object
            file_path: Path to image file
            
        Returns:
            Dictionary containing metadata
        """
        metadata = {
            'format': img.format,
            'mode': img.mode,
            'size': img.size,
            'original_size': os.path.getsize(file_path),
            'dpi': img.info.get('dpi'),
            'icc_profile': bool(img.info.get('icc_profile')),
            'exif': bool(hasattr(img, '_getexif') and img._getexif() is not None)
        }
        
        # Extract EXIF data if available
        if metadata['exif']:
            try:
                exif = img._getexif()
                metadata['exif_data'] = {
                    ExifTags.TAGS.get(tag, tag): value
                    for tag, value in exif.items()
                    if tag in ExifTags.TAGS
                }
            except Exception as e:
                self.logger.warning(f"Failed to extract EXIF data: {e}")
        
        return metadata

    def _optimize_image(self, img: Image.Image) -> Image.Image:
        """Optimize image for web.
        
        Args:
            img: PIL Image object
            
        Returns:
            Optimized image
        """
        # Convert RGBA to RGB if alpha channel is not needed
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        
        # Convert to RGB if not already
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        
        # Resize if too large
        max_size = (1920, 1080)
        if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
            img.thumbnail(max_size, Image.LANCZOS)
        
        return img

    def _get_metadata_path(self, input_path: Path) -> Path:
        """Get path for metadata file.
        
        Args:
            input_path: Input image path
            
        Returns:
            Path for metadata file
        """
        rel_path = input_path.relative_to(self.paths.input_dir)
        return Path(self.paths.image_dirs['metadata']) / f"{rel_path.stem}.json"

    def _save_metadata(self, metadata_path: Path, metadata: Dict[str, Any]) -> None:
        """Save metadata to file.
        
        Args:
            metadata_path: Path to save metadata
            metadata: Metadata to save
        """
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)

    def _is_cached(self, input_path: Path) -> bool:
        """Check if image is cached.
        
        Args:
            input_path: Input image path
            
        Returns:
            True if image is cached
        """
        if str(input_path) not in self.cache:
            return False
            
        cached = self.cache[str(input_path)]
        if not os.path.exists(cached['output_path']):
            return False
            
        input_mtime = os.path.getmtime(input_path)
        cache_mtime = os.path.getmtime(cached['output_path'])
        
        return input_mtime <= cache_mtime

    def _get_cached_result(self, input_path: Path) -> Dict[str, Any]:
        """Get cached processing result.
        
        Args:
            input_path: Input image path
            
        Returns:
            Cached result dictionary
        """
        return self.cache[str(input_path)]

    def _cache_result(self, input_path: Path, result: Dict[str, Any]) -> None:
        """Cache processing result.
        
        Args:
            input_path: Input image path
            result: Result to cache
        """
        self.cache[str(input_path)] = result
        self._save_cache()

    def _load_cache(self) -> None:
        """Load cache from file."""
        cache_path = self.paths.image_dirs['cache'] / 'image_cache.json'
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    self.cache = json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load cache: {e}")
                self.cache = {}

    def _save_cache(self) -> None:
        """Save cache to file."""
        cache_path = self.paths.image_dirs['cache'] / 'image_cache.json'
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(cache_path, 'w') as f:
                json.dump(self.cache, f, indent=2, default=str)
        except Exception as e:
            self.logger.warning(f"Failed to save cache: {e}")