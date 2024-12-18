"""Image processor for handling image conversions and descriptions."""

import os
import shutil
import tempfile
import base64
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
import json
import time

from PIL import Image
import pillow_heif
from openai import OpenAI

from ..core.config import NovaConfig, ImageProcessingConfig
from ..core.errors import ProcessingError
from ..core.logging import get_logger

logger = get_logger(__name__)

@dataclass
class ImageMetadata:
    """Metadata for processed images."""
    original_path: str
    processed_path: str
    description: Optional[str]
    width: int
    height: int
    format: str
    size: int
    created_at: float
    processing_time: float
    error: Optional[str] = None

class ImageProcessor:
    """Handles image processing operations."""

    def __init__(self, config: NovaConfig, openai_client: Optional[OpenAI] = None):
        """Initialize image processor."""
        self.config = config
        self.image_config = config.image
        self.openai_client = openai_client
        self.vision_api_available = False
        self._setup_directories()
        if openai_client:
            self._validate_vision_api()
            if self.vision_api_available:
                self._clear_cache()

    def _setup_directories(self) -> None:
        """Create required directories."""
        # Create base directory first
        self.image_config.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.image_config.original_dir.mkdir(parents=True, exist_ok=True)
        self.image_config.processed_dir.mkdir(parents=True, exist_ok=True)
        self.image_config.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.image_config.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug("Created image processing directories", extra={
            "base_dir": str(self.image_config.base_dir),
            "original_dir": str(self.image_config.original_dir),
            "processed_dir": str(self.image_config.processed_dir),
            "metadata_dir": str(self.image_config.metadata_dir),
            "cache_dir": str(self.image_config.cache_dir)
        })

    def _get_cache_path(self, image_path: Path) -> Path:
        """Get cache file path for an image."""
        cache_name = f"{image_path.stem}_{image_path.stat().st_mtime}.json"
        return self.image_config.cache_dir / cache_name

    def _clear_cache(self) -> None:
        """Clear the cache directory."""
        try:
            removed_files = 0
            for cache_file in self.image_config.cache_dir.glob("*.json"):
                try:
                    # Validate cache entry
                    with open(cache_file, 'r') as f:
                        data = json.load(f)
                    if not data.get('description'):
                        logger.debug("Removing invalid cache file", extra={
                            "file": str(cache_file),
                            "reason": "no description"
                        })
                        cache_file.unlink()
                        removed_files += 1
                except Exception as e:
                    logger.debug("Removing corrupted cache file", extra={
                        "file": str(cache_file),
                        "error": str(e)
                    })
                    cache_file.unlink()
                    removed_files += 1
            
            if removed_files > 0:
                logger.info(f"Cleaned {removed_files} cache files")
        except Exception as e:
            logger.error("Failed to clear cache", extra={"error": str(e)})

    def _load_from_cache(self, image_path: Path) -> Optional[ImageMetadata]:
        """Load image metadata from cache if available and valid."""
        if not self.image_config.cache_enabled or not self.vision_api_available:
            return None

        cache_path = self._get_cache_path(image_path)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            
            # Check cache expiration
            if time.time() - data['created_at'] > self.image_config.cache_duration:
                logger.debug(f"Cache expired for {image_path}")
                cache_path.unlink()
                return None

            # Ensure cache has description
            if not data.get('description'):
                logger.debug(f"Cache entry has no description for {image_path}")
                cache_path.unlink()
                return None

            return ImageMetadata(**data)
        except Exception as e:
            logger.warning(f"Failed to load cache for {image_path}: {e}")
            try:
                cache_path.unlink()
            except Exception:
                pass
            return None

    def _save_to_cache(self, image_path: Path, metadata: ImageMetadata) -> None:
        """Save image metadata to cache."""
        if not self.image_config.cache_enabled:
            return

        # Don't cache results without descriptions
        if metadata.description is None:
            logger.debug(f"Skipping cache for {image_path} - no description available")
            return

        cache_path = self._get_cache_path(image_path)
        try:
            with open(cache_path, 'w') as f:
                json.dump(metadata.__dict__, f)
        except Exception as e:
            logger.warning(f"Failed to save cache for {image_path}: {e}")

    def _validate_vision_api(self) -> None:
        """Validate access to OpenAI Vision API."""
        try:
            logger.debug("Testing OpenAI Vision API access")
            
            # Test with a tiny 1x1 transparent PNG
            test_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-2024-04-09",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Test image."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{test_image}",
                                "detail": "low"
                            }
                        }
                    ]
                }],
                max_tokens=1
            )
            
            self.vision_api_available = True
            logger.info("OpenAI Vision API access validated")
            
        except Exception as e:
            self.vision_api_available = False
            logger.error("OpenAI Vision API validation failed", extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "has_response": hasattr(e, 'response')
            })

    def _get_image_description(self, image_path: Path) -> Optional[str]:
        """Get image description using OpenAI."""
        if not self.openai_client or not self.vision_api_available:
            return None

        try:
            with open(image_path, 'rb') as img_file:
                image_data = base64.b64encode(img_file.read()).decode('utf-8')

            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-2024-04-09",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Describe this image in detail, focusing on its content, context, and any visible text or important elements."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}",
                                "detail": "high"
                            }
                        }
                    ]
                }],
                max_tokens=500
            )
            
            if not response.choices:
                logger.error("No response choices returned from OpenAI")
                return None
                
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Failed to get image description: {str(e)}")
            return None

    def _format_markdown(self, metadata: ImageMetadata) -> str:
        """Format image metadata as markdown."""
        lines = [
            f"# Image: {Path(metadata.original_path).name}",
            ""
        ]
        
        if metadata.description:
            lines.extend([
                "## Description",
                "",
                metadata.description,
                ""
            ])
        
        lines.extend([
            "## Metadata",
            "",
            f"- Original Format: {Path(metadata.original_path).suffix[1:].upper()}",
            f"- Converted Format: {metadata.format}",
            f"- Dimensions: {metadata.width}x{metadata.height}",
            f"- Size: {metadata.size / 1024:.1f} KB",
            ""
        ])
        
        if metadata.error:
            lines.extend([
                "## Processing Errors",
                "",
                f"⚠️ {metadata.error}",
                ""
            ])
        
        if not metadata.description and self.openai_client:
            if self.vision_api_available:
                lines.extend([
                    "## Note",
                    "",
                    "*Image description generation failed. Please check the logs for details.*",
                    ""
                ])
            else:
                lines.extend([
                    "## Note",
                    "",
                    "*Image description not available - Vision API access required.*",
                    ""
                ])
        
        return "\n".join(lines)

    def process_image(self, input_path: Path, output_dir: Path) -> ImageMetadata:
        """Process an image file."""
        start_time = time.time()
        logger.info("Processing image %s", input_path.name)
        
        try:
            # Create output directory if it doesn't exist
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Check cache only if we have vision API access
            cached = None
            if self.vision_api_available:
                cached = self._load_from_cache(input_path)
            if cached:
                logger.debug("Using cached result for %s", input_path.name)
                return cached
            
            # Save original
            original_path = self.image_config.original_dir / input_path.name
            shutil.copy2(input_path, original_path)
            
            # Determine output format and path
            output_format = self.image_config.preferred_format.lower()
            output_filename = f"{input_path.stem}.{output_format}"
            processed_path = output_dir / output_filename
            
            logger.debug("Converting %s to %s", input_path.name, output_format.upper())
            
            # Handle HEIC files specifically
            if input_path.suffix.lower() == '.heic':
                logger.debug("Converting HEIC file")
                heif_file = pillow_heif.read_heif(str(input_path))
                image = Image.frombytes(
                    heif_file.mode,
                    heif_file.size,
                    heif_file.data,
                    "raw",
                )
            else:
                image = Image.open(input_path)
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
                logger.debug("Converting image mode from %s to RGB", image.mode)
                image = image.convert('RGB')
            
            # Resize if needed while maintaining aspect ratio
            if image.width > self.image_config.max_width or image.height > self.image_config.max_height:
                logger.debug("Resizing image from %dx%d to max %dx%d", 
                    image.width, image.height,
                    self.image_config.max_width, self.image_config.max_height
                )
                image.thumbnail((self.image_config.max_width, self.image_config.max_height))
            
            # Save with specified quality
            image.save(
                processed_path,
                format=output_format.upper(),
                quality=self.image_config.quality,
                optimize=True
            )
            
            # Get image description
            description = self._get_image_description(processed_path)
            if description:
                logger.debug("Generated description (%d chars)", len(description))
            else:
                logger.debug("No image description available")
            
            # Create metadata
            metadata = ImageMetadata(
                original_path=str(original_path),
                processed_path=str(processed_path),
                description=description,
                width=image.width,
                height=image.height,
                format=output_format.upper(),
                size=processed_path.stat().st_size,
                created_at=time.time(),
                processing_time=time.time() - start_time
            )
            
            # Save metadata
            metadata_path = self.image_config.metadata_dir / f"{input_path.stem}.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata.__dict__, f, indent=2)
            
            # Save markdown
            markdown_path = output_dir / f"{input_path.stem}.md"
            with open(markdown_path, 'w') as f:
                f.write(self._format_markdown(metadata))
            
            # Cache result
            self._save_to_cache(input_path, metadata)
            
            logger.info("Completed processing %s (%.2fs)", input_path.name, metadata.processing_time)
            
            return metadata
            
        except Exception as e:
            error_msg = f"Failed to process image {input_path}: {str(e)}"
            logger.error("Failed to process %s: %s", input_path.name, str(e))
            
            metadata = ImageMetadata(
                original_path=str(input_path),
                processed_path="",
                description=None,
                width=0,
                height=0,
                format="",
                size=0,
                created_at=time.time(),
                processing_time=time.time() - start_time,
                error=error_msg
            )
            
            # Save error markdown
            markdown_path = output_dir / f"{input_path.stem}.md"
            with open(markdown_path, 'w') as f:
                f.write(self._format_markdown(metadata))
            
            return metadata 