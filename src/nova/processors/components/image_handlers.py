"""Image handling components for Nova processors."""

from pathlib import Path
from typing import Dict, Any, Optional
import json
from PIL import Image
from openai import OpenAI
import io
import base64

from . import ImageComponent
from ...core.errors import ImageProcessingError
from ...core.config import NovaConfig, ProcessorConfig
from ...core.logging import get_logger

class OpenAIImageHandler(ImageComponent):
    """Handles image processing using OpenAI Vision."""
    
    def __init__(self, processor_config: ProcessorConfig, nova_config: NovaConfig):
        """Initialize handler.
        
        Args:
            processor_config: Processor-specific configuration
            nova_config: Global Nova configuration
        """
        super().__init__(processor_config, nova_config)
        self.logger = get_logger(self.__class__.__name__)
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=nova_config.openai.api_key)
        
        # Add component-specific stats
        self.stats.update({
            'images_processed': 0,
            'descriptions_generated': 0,
            'cache_hits': 0,
            'heic_conversions': 0
        })
    
    def process_image(self, input_path: Path, output_path: Path) -> Dict[str, Any]:
        """Process an image file.
        
        Args:
            input_path: Path to input image
            output_path: Path to output image
            
        Returns:
            Dictionary containing image metadata
        """
        try:
            # Check cache first
            cache_key = str(input_path)
            cached_result = self._load_from_cache(cache_key)
            if cached_result:
                self.stats['cache_hits'] += 1
                return cached_result
            
            # Convert HEIC to JPEG if needed
            if input_path.suffix.lower() in ['.heic']:
                temp_path = self.config.paths.temp_dir / f"{input_path.stem}.jpg"
                self._convert_heic_to_jpeg(input_path, temp_path)
                self.stats['heic_conversions'] += 1
                img_path = temp_path
            else:
                img_path = input_path
            
            # Load and process image
            with Image.open(img_path) as img:
                # Extract metadata
                metadata = {
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'original_path': str(input_path)
                }
                
                # Generate description if enabled
                if self.config.processors.image.openai.enabled:
                    description = self._generate_description(img)
                    metadata['description'] = description
                    self.stats['descriptions_generated'] += 1
                
                # Optimize and save image
                output_path.parent.mkdir(parents=True, exist_ok=True)
                self._optimize_image(img, output_path)
            
            # Update stats
            self.stats['images_processed'] += 1
            
            # Cache result
            self._cache_result(cache_key, metadata)
            
            # Clean up temp file if created
            if input_path.suffix.lower() in ['.heic']:
                temp_path.unlink(missing_ok=True)
            
            return metadata
            
        except Exception as e:
            raise ImageProcessingError(f"Failed to process {input_path}: {e}") from e
    
    def _convert_heic_to_jpeg(self, input_path: Path, output_path: Path) -> None:
        """Convert HEIC image to JPEG.
        
        Args:
            input_path: Path to HEIC image
            output_path: Path to save JPEG image
        """
        try:
            from PIL import Image
            import pillow_heif
            
            # Register HEIF opener
            pillow_heif.register_heif_opener()
            
            # Open and convert HEIC image
            with Image.open(input_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Save as JPEG
                img.save(output_path, 'JPEG', quality=95)
                
        except Exception as e:
            raise ImageProcessingError(f"Failed to convert HEIC to JPEG: {e}") from e
    
    def _generate_description(self, image: Image.Image) -> str:
        """Generate image description using OpenAI Vision.
        
        Args:
            image: PIL Image object
            
        Returns:
            Generated description
        """
        try:
            # Convert image to JPEG bytes
            img_byte_arr = io.BytesIO()
            if image.mode != 'RGB':
                image = image.convert('RGB')
            image.save(img_byte_arr, format='JPEG', quality=95)
            img_byte_arr = img_byte_arr.getvalue()
            
            import base64
            base64_image = base64.b64encode(img_byte_arr).decode('utf-8')
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.config.processors.image.openai.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Please describe this image in detail."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.config.processors.image.openai.max_tokens,
                temperature=self.config.processors.image.openai.temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.warning(f"Failed to generate description: {e}")
            return ""
    
    def _optimize_image(self, image: Image.Image, output_path: Path) -> None:
        """Optimize and save image.
        
        Args:
            image: PIL Image object
            output_path: Path to save optimized image
        """
        try:
            # Convert to RGB if needed
            if image.mode in ['RGBA', 'P']:
                image = image.convert('RGB')
            
            # Resize if needed
            max_size = self.config.processors.image.max_size
            if image.size[0] * image.size[1] * 3 > max_size:
                ratio = (max_size / (image.size[0] * image.size[1] * 3)) ** 0.5
                new_size = tuple(int(dim * ratio) for dim in image.size)
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Save with quality setting
            image.save(
                output_path,
                quality=self.config.processors.image.quality,
                optimize=True
            )
            
        except Exception as e:
            raise ImageProcessingError(f"Failed to optimize image: {e}") from e
    
    def _load_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Load result from cache.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached result or None if not found
        """
        try:
            cache_path = Path(self.config.paths.image_dirs["cache"]) / f"{cache_key}.json"
            if cache_path.exists():
                with open(cache_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load from cache: {e}")
        return None
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Cache processing result.
        
        Args:
            cache_key: Cache key
            result: Result to cache
        """
        try:
            cache_path = Path(self.config.paths.image_dirs["cache"]) / f"{cache_key}.json"
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, 'w') as f:
                json.dump(result, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to cache result: {e}")