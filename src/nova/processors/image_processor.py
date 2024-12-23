"""Image processor module for Nova document processor."""

import os
import shutil
import tempfile
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import json
import time
import re
import logging
import subprocess

from PIL import Image
import pillow_heif
from openai import OpenAI
from rich.console import Console

from .base import BaseProcessor
from .components.image_handlers import OpenAIImageHandler
from ..core.config import ProcessorConfig, NovaConfig
from ..core.errors import ProcessingError, ConfigurationError
from ..core.logging import get_logger
from ..core.openai import OpenAIClient
from ..core.summary import ProcessingSummary

logger = get_logger(__name__)
console = Console()

# Create logs directory
Path('logs').mkdir(exist_ok=True)

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

class ImageProcessor(BaseProcessor):
    """Handles image processing operations."""

    def __init__(self, processor_config: ProcessorConfig, nova_config: NovaConfig):
        """Initialize processor.
        
        Args:
            processor_config: Processor-specific configuration
            nova_config: Global Nova configuration
        """
        super().__init__(processor_config, nova_config)
        self.image_config = processor_config
        self.vision_api_available = False
        
        # Initialize OpenAI client
        self._init_openai_client()
        
        # Initialize stats
        self.stats = {
            'total_processed': 0,
            'descriptions_generated': 0,
            'heic_conversions': 0,
            'cache_hits': 0,
            'api_calls': 0,
            'api_time_total': 0.0,
            'images_processed': 0,
            'errors': 0
        }
        
        # Setup directories
        self._setup_directories()

        # Store a record of files that changed extensions
        self.converted_files = {}  # { "old_filename.ext": "new_filename.ext", ... }

    def _setup_directories(self) -> None:
        """Create required directories."""
        # Create base directory first
        base_dir = self.nova_config.paths.processing_dir / 'images'
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        original_dir = base_dir / 'original'
        processed_dir = base_dir / 'processed'
        metadata_dir = base_dir / 'metadata'
        cache_dir = base_dir / 'cache'
        
        original_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)
        metadata_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug("Created image processing directories", extra={
            "base_dir": str(base_dir),
            "original_dir": str(original_dir),
            "processed_dir": str(processed_dir),
            "metadata_dir": str(metadata_dir),
            "cache_dir": str(cache_dir)
        })

    def _get_cache_path(self, image_path: Path) -> Path:
        """Get cache file path for an image."""
        cache_name = f"{image_path.stem}_{image_path.stat().st_mtime}.json"
        return self.nova_config.paths.image_dirs['cache'] / cache_name

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
            logger.debug(f"Cache disabled or Vision API unavailable for {image_path.name}")
            return None

        cache_path = self._get_cache_path(image_path)
        if not cache_path.exists():
            logger.debug(f"No cache found for {image_path.name}")
            return None

        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            
            # Check cache expiration
            if time.time() - data['created_at'] > self.image_config.cache_duration:
                logger.info(f"Cache expired for {image_path.name}")
                cache_path.unlink()
                return None

            # Ensure cache has description
            if not data.get('description'):
                logger.info(f"Invalid cache entry for {image_path.name} (no description)")
                cache_path.unlink()
                return None

            logger.info(f"Using cached data for {image_path.name}")
            return ImageMetadata(**data)
        except Exception as e:
            logger.warning(f"Failed to load cache for {image_path.name}: {e}")
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
                model="gpt-4-vision-preview",  # Use vision model for testing
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Test connection"
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

    def _generate_image_description(self, image_path: Path) -> Optional[str]:
        """Generate a description for an image using OpenAI's vision model."""
        if not self.vision_api_available or not self.openai_client:
            logger.warning("Vision API not available - skipping description generation")
            return None
            
        try:
            # Read image and encode as base64
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                
            response = self.openai_client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Please describe this image in detail, focusing on its key visual elements and composition."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            
            self.stats['api_calls'] += 1
            description = response.choices[0].message.content
            if description:
                self.stats['descriptions_generated'] += 1
                
                # Use correct path from nova_config
                metadata_dir = self.nova_config.paths.image_dirs['metadata']
                metadata_path = metadata_dir / f"{image_path.stem}_description.md"
                metadata_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(metadata_path, 'w') as f:
                    f.write(f"# Image Description: {image_path.name}\n\n")
                    f.write(description)
                    
                logger.info(f"Saved image description to {metadata_path}")
                
            return description
            
        except Exception as e:
            logger.error(f"Failed to generate image description: {str(e)}", exc_info=True)
            self.stats['errors'] += 1
            return None

    def _format_markdown(self, metadata: ImageMetadata) -> str:
        """Format image metadata as markdown."""
        lines = []
        
        # Add header with image name
        lines.extend([
            f"# Image: {Path(metadata.original_path).name}",
            ""
        ])
        
        # Add description in a collapsible section if available
        if metadata.description:
            lines.extend([
                "## Description",
                "",
                "<details>",
                "<summary>Click to expand description</summary>",
                "",
                metadata.description,
                "</details>",
                ""
            ])
        
        # Add technical metadata in a table
        lines.extend([
            "## Technical Details",
            "",
            "| Property | Value |",
            "|----------|-------|",
            f"| Original Format | {Path(metadata.original_path).suffix[1:].upper()} |",
            f"| Processed Format | {metadata.format} |",
            f"| Dimensions | {metadata.width}x{metadata.height} pixels |",
            f"| File Size | {metadata.size / 1024:.1f} KB |",
            f"| Processing Time | {metadata.processing_time:.2f} seconds |",
            ""
        ])
        
        # Add processing status
        if metadata.error:
            lines.extend([
                "## Processing Errors",
                "",
                f"⚠️ {metadata.error}",
                ""
            ])
        elif not metadata.description and self.openai_client:
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

    def _cleanup_temp_files(self, temp_files: List[Path]) -> None:
        """Clean up temporary files only."""
        for temp_file in temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    logger.debug(f"Cleaned up temporary file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {temp_file}: {e}")

    def _process_image(self, input_path: Path, output_path: Path) -> Path:
        """Process an image file."""
        if input_path.suffix.lower() == '.heic':
            # Convert HEIC to PNG using sips
            png_output = output_path.with_suffix('.png')
            subprocess.run(['sips', '-s', 'format', 'png', str(input_path), '--out', str(png_output)], check=True)
            return png_output
        else:
            # Copy other images as is
            shutil.copy2(input_path, output_path)
            return output_path

    def process(self, input_path: Path, output_path: Path) -> Path:
        """Process an image file.
        
        Args:
            input_path: Path to input image
            output_path: Path to output image
            
        Returns:
            Path to processed image
        """
        try:
            # Create output directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Process image based on type
            suffix = input_path.suffix.lower()
            if suffix == '.svg':
                # SVG files are copied without processing
                shutil.copy2(input_path, output_path)
                self.stats['images_processed'] += 1
                return output_path
            elif suffix in ['.heic', '.heif']:
                # Convert HEIC to JPEG
                heif_file = pillow_heif.read_heif(str(input_path))
                img = Image.frombytes(
                    heif_file.mode,
                    heif_file.size,
                    heif_file.data,
                    "raw",
                    heif_file.mode,
                    heif_file.stride,
                )
                output_path = output_path.with_suffix('.jpg')
                img = img.convert('RGB')
                self.stats['heic_conversions'] += 1
                img.save(output_path, optimize=True, quality=85)
            else:
                # Process other image types
                with Image.open(input_path) as img:
                    img.save(output_path, optimize=True, quality=85)
            
            # Update stats
            self.stats['images_processed'] += 1
            
            return output_path
            
        except Exception as e:
            self.logger.error(f"Failed to process {input_path}: {e}")
            self.stats['errors'] += 1
            raise ProcessingError(f"Failed to process {input_path}: {e}") from e

    def _setup(self) -> None:
        """Setup image processor requirements."""
        # Initialize OpenAI client
        try:
            self.openai_client = OpenAIClient()
            if self.openai_client:
                logger.info("OpenAI integration enabled - image descriptions will be generated")
            else:
                logger.warning("OpenAI integration disabled - image descriptions will be limited")
        except ConfigurationError as e:
            logger.error(f"OpenAI configuration error: {str(e)}")
            logger.warning("Continuing without OpenAI integration - image descriptions will be limited")
            self.openai_client = None
        
        # Initialize processing summary
        self.summary = ProcessingSummary()
        
        # Initialize stats
        self.stats = {
            'api_calls': 0,
            'api_time_total': 0.0,
            'cache_hits': 0,
            'images_processed': 0,
            'images_with_descriptions': 0,
            'images_failed': 0
        }

    def _init_openai_client(self) -> None:
        """Initialize OpenAI client."""
        try:
            self.openai_client = OpenAIClient()
            if self.openai_client:
                logger.info("OpenAI client initialized successfully")
                self.vision_api_available = True
            else:
                logger.warning("OpenAI client not available - image descriptions will be limited")
                self.vision_api_available = False
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.vision_api_available = False
            self.openai_client = None

    def process_image(self, image_file: Path, metadata: dict = None) -> str:
        """Process an image file and generate a description.

        Args:
            image_file: Path to the image file
            metadata: Optional metadata for the image

        Returns:
            Generated description for the image
        """
        if not image_file.exists():
            logger.warning(f"Image file not found: {image_file}")
            return f"[Image not found: {image_file.name}]"

        try:
            # Use provided description from metadata if available
            if metadata and 'description' in metadata:
                return metadata['description']

            # Generate description using OpenAI Vision API if available
            if self.openai_client:
                try:
                    with open(image_file, 'rb') as f:
                        image_data = f.read()
                        response = self.openai_client.chat.completions.create(
                            model="gpt-4-vision-preview",
                            messages=[
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": "Please describe this image in a concise way."},
                                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(image_data).decode()}"}}
                                    ]
                                }
                            ],
                            max_tokens=100
                        )
                        return response.choices[0].message.content
                except Exception as e:
                    logger.error(f"Error generating image description: {str(e)}")
                    return f"[Image: {image_file.name}]"
            else:
                # Return basic description if OpenAI is not available
                return f"[Image: {image_file.name}]"

        except Exception as e:
            logger.error(f"Error processing image {image_file}: {str(e)}")
            return f"[Error processing image: {image_file.name}]"