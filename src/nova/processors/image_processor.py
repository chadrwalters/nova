from typing import Optional
from pathlib import Path
import time
from PIL import Image
from nova.models.image_metadata import ImageMetadata
from nova.utils.console import console
import base64
from nova.utils.openai import setup_openai_client

class ImageProcessor:
    def __init__(self, config, logger):
        """Initialize the image processor.
        
        Args:
            config: Configuration object
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.start_time = time.time()
        
        # Initialize stats
        self.stats = {
            'total': 0,
            'processed': 0,
            'with_description': 0,
            'failed': 0,
            'heic_converted': 0,
            'total_original_size': 0,
            'total_processed_size': 0,
            'cache_hits': 0,
            'api_calls': 0
        }
        
        # Load cache
        self.cache = {}
        self.cache_file = self.config.image.cache_dir / 'cache.json'
        self._load_cache()
        
        # Set up OpenAI client
        self.vision_api_available = False
        try:
            self.openai_client = setup_openai_client()
            self.vision_api_available = True
            self.logger.info("OpenAI client initialized successfully")
        except Exception as e:
            self.logger.warning(f"Failed to initialize OpenAI client: {e}")
        
        # Image processing settings
        self.max_width = 1920
        self.max_height = 1080
        self.quality = 85
        self.optimize = True
        
    def process_image(self, input_path: Path, output_dir: Path) -> Optional[ImageMetadata]:
        """Process an image file.
        
        Args:
            input_path: Path to input image
            output_dir: Directory to save processed image
            
        Returns:
            ImageMetadata if successful, None if failed
        """
        try:
            # Generate hash for image
            image_hash = self._hash_file(input_path)
            
            # Check cache first
            if self._load_from_cache(image_hash):
                self.logger.info(f"Using cached data for {input_path.name}")
                return self.cache[image_hash]
            
            # Load and process image
            image = Image.open(input_path)
            
            # Convert HEIC to PNG if needed
            if input_path.suffix.lower() in ['.heic', '.heif']:
                image = self._convert_heic(input_path)
                self.stats['heic_converted'] += 1
            
            # Resize if needed
            original_size = image.size
            if self._needs_resize(image):
                image = self._resize_image(image)
                console.print(f"Resizing image {original_size[0]}x{original_size[1]} → max {self.max_width}x{self.max_height}")
            
            # Save processed image
            output_path = output_dir / f"{image_hash}.png"
            output_dir.mkdir(parents=True, exist_ok=True)
            image.save(output_path, format='PNG', optimize=True)
            
            # Generate description if OpenAI available
            description = None
            if self.vision_api_available:
                try:
                    description = self._generate_description(input_path)
                    if description:
                        console.print(f"Generated description ({len(description)} chars)")
                except Exception as e:
                    self.logger.warning(f"Failed to generate description: {e}")
            
            # Create metadata
            metadata = ImageMetadata(
                original_path=str(input_path),
                processed_path=str(output_path),
                width=image.size[0],
                height=image.size[1],
                format='PNG',
                size=output_path.stat().st_size,
                description=description,
                processing_time=time.time() - self.start_time
            )
            
            # Update stats
            original_size = input_path.stat().st_size
            processed_size = output_path.stat().st_size
            size_diff = processed_size - original_size
            size_change_pct = (size_diff / original_size) * 100
            
            console.print(
                f"Image processed: {original_size[0]}x{original_size[1]} → "
                f"{image.size[0]}x{image.size[1]}, "
                f"{original_size/1024:.1f}KB → {processed_size/1024:.1f}KB "
                f"({size_change_pct:+.1f}% {'larger' if size_change_pct > 0 else 'smaller'})"
            )
            
            # Cache metadata
            self.cache[image_hash] = metadata
            self._save_cache()
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to process image {input_path}: {e}")
            return None 
        
    def _generate_description(self, image_path: Path) -> Optional[str]:
        """Generate a description for an image using OpenAI's vision model.
        
        Args:
            image_path: Path to the image
            
        Returns:
            Description string or None if generation failed
        """
        try:
            if not self.vision_api_available:
                self.logger.warning("OpenAI client not available - skipping description generation")
                return None
            
            # Encode image
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Call OpenAI API
            response = self.openai_client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Please describe this image in detail, focusing on its content, composition, and any notable elements. Include both high-level overview and specific details that would be relevant for documentation or accessibility purposes."
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
                max_tokens=1000
            )
            
            # Extract description
            description = response.choices[0].message.content
            if description:
                self.stats['api_calls'] += 1
                self.logger.info(f"Generated description ({len(description)} chars)")
                return description
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Failed to generate description: {e}")
            return None 