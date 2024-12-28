"""Image file handler with vision API integration."""

import io
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union
import base64
import tempfile
from PIL import Image
import openai
from ..models.document import DocumentMetadata
from .base import BaseHandler
from ..config.manager import ConfigManager
import logging
import shutil

# Set httpx and urllib3 loggers to WARNING level
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

class ImageHandler(BaseHandler):
    """Handler for image files with vision API integration."""
    
    name = "image"
    version = "0.1.0"
    file_types = ["jpg", "jpeg", "png", "gif", "webp", "heic"]
    
    def __init__(self, config: ConfigManager) -> None:
        """Initialize handler.
        
        Args:
            config: Nova configuration manager.
        """
        super().__init__(config)
        self.name = "Image Handler"
        self.version = "0.1.0"
        self.file_types = ["jpg", "jpeg", "png", "gif", "webp", "heic"]
        
        # Initialize OpenAI client
        self.openai_client = None
        self.openai_model = None
        self.openai_max_tokens = None
        self.vision_prompt = None
        
        # Configure logging for openai to be less verbose
        openai_logger = logging.getLogger("openai")
        openai_logger.setLevel(logging.WARNING)
        
        # Configure httpx logger to be less verbose
        httpx_logger = logging.getLogger("httpx")
        httpx_logger.setLevel(logging.WARNING)
        
        # Configure PIL logger to be less verbose
        pil_logger = logging.getLogger("PIL")
        pil_logger.setLevel(logging.WARNING)
        
        # Initialize OpenAI client if configured
        if hasattr(config.config, 'apis') and hasattr(config.config.apis, 'openai'):
            openai_config = config.config.apis.openai
            # Try environment variable first, then config
            api_key = os.environ.get('OPENAI_API_KEY')
            if not api_key:  # If not in environment, try config
                api_key = getattr(openai_config, 'api_key', None)
            
            if api_key:
                self.openai_client = openai.OpenAI(api_key=api_key)
                self.openai_model = "gpt-4o"  # Update to use gpt-4o model
                self.openai_max_tokens = getattr(openai_config, 'max_tokens', 500)
                self.vision_prompt = getattr(openai_config, 'vision_prompt', (
                    "Please analyze this image and provide a detailed description. "
                    "If it's a screenshot, extract any visible text. "
                    "If it's a photograph, describe the scene and key elements. "
                    "Focus on what makes this image relevant in a note-taking context."
                ))
            else:
                self.logger.warning("OpenAI API key not found in environment or config - image analysis will be disabled")
        else:
            self.logger.warning("OpenAI API not configured - image analysis will be disabled")
        
    def _convert_heic(self, file_path: Path, output_path: Path) -> None:
        """Convert HEIC file to JPEG.
        
        Args:
            file_path: Path to HEIC file.
            output_path: Path to output JPEG file.
            
        Raises:
            ValueError: If conversion fails.
        """
        try:
            # Create output directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use sips to convert HEIC to JPEG
            result = subprocess.run(
                ["sips", "-s", "format", "jpeg", str(file_path), "--out", str(output_path)],
                capture_output=True,
                text=True,
            )
            
            if result.returncode != 0:
                raise ValueError(f"sips conversion failed: {result.stderr}")
            
            # Verify the output file exists and is readable
            if not output_path.exists():
                raise ValueError("Conversion succeeded but output file not found")
            
            try:
                # Verify the output is a valid JPEG
                with Image.open(output_path) as img:
                    img.verify()
            except Exception as e:
                raise ValueError(f"Converted file is not a valid JPEG: {str(e)}")
                
        except Exception as e:
            raise ValueError(f"Failed to convert HEIC to JPEG: {e}")

    def _get_relative_path(self, from_path: Path, to_path: Path) -> str:
        """Get relative path from one file to another.
        
        Args:
            from_path: Path to start from.
            to_path: Path to end at.
            
        Returns:
            Relative path from from_path to to_path.
        """
        # Get relative path from markdown file to original file
        try:
            rel_path = os.path.relpath(to_path, from_path.parent)
            return rel_path.replace("\\", "/")  # Normalize path separators
        except ValueError:
            # If paths are on different drives, use absolute path
            return str(to_path).replace("\\", "/")

    async def _get_image_context(self, image_path: Path) -> str:
        """Get image context using OpenAI's vision API.
        
        Args:
            image_path: Path to image file.
            
        Returns:
            Context description from vision API.
            
        Raises:
            ValueError: If the image file is invalid or cannot be processed.
            openai.RateLimitError: If the API rate limit is exceeded.
            openai.AuthenticationError: If the API key is invalid.
            openai.APIError: If there's an error with the OpenAI API.
        """
        # If OpenAI client is not configured, return basic image info
        if not self.openai_client:
            try:
                with Image.open(image_path) as img:
                    width, height = img.size
                    mode = img.mode
                    format = img.format
                    return f"Image: {width}x{height} pixels, {mode} mode, {format} format"
            except Exception as e:
                self.logger.error(f"Failed to get basic image info: {str(e)}")
                return "No context available - Failed to read image"
        
        try:
            # If it's a HEIC file, convert to JPEG first
            temp_path = None
            if image_path.suffix.lower() == '.heic':
                temp_path = Path(tempfile.mkdtemp()) / f"{image_path.stem}.jpg"
                try:
                    self._convert_heic(image_path, temp_path)
                    image_path = temp_path
                except Exception as e:
                    self.logger.error(f"Failed to convert HEIC to JPEG: {str(e)}")
                    return "No context available - Failed to convert HEIC to JPEG"
            
            try:
                # Read image and convert to base64
                with open(image_path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                
                # Call OpenAI Vision API with updated format
                response = self.openai_client.chat.completions.create(
                    model=self.openai_model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": self.vision_prompt
                                },
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
                    max_tokens=self.openai_max_tokens
                )
                
                return response.choices[0].message.content
                
            except openai.RateLimitError as e:
                self.logger.error(f"OpenAI API rate limit exceeded: {str(e)}")
                return "No context available - API rate limit exceeded. Please try again later."
                
            except openai.AuthenticationError as e:
                self.logger.error(f"OpenAI API authentication failed: {str(e)}")
                return "No context available - API authentication failed. Please check your API key."
                
            except openai.APIError as e:
                self.logger.error(f"OpenAI API error: {str(e)}")
                return "No context available - API error. Please try again later."
                
            finally:
                # Clean up temporary file if we created one
                if temp_path and temp_path.exists():
                    try:
                        temp_path.unlink()
                        temp_path.parent.rmdir()
                    except Exception:
                        pass
                
        except Exception as e:
            # Get error message without any potential base64 data
            error_str = str(e)
            if len(error_str) > 100:  # If error message is too long (likely contains base64)
                error_str = f"{error_str[:100]}... [truncated]"
            
            self.logger.error(f"Failed to get image context for {image_path.name}: {error_str}")
            return "No context available - Image processing error"

    def _classify_image_type(self, image_path: Path) -> str:
        """Classify image as screenshot, photograph, or diagram.
        
        Args:
            image_path: Path to image file.
            
        Returns:
            Image type classification.
        """
        try:
            # If it's a HEIC file, convert to JPEG first
            temp_path = None
            if image_path.suffix.lower() == '.heic':
                temp_path = Path(tempfile.mkdtemp()) / f"{image_path.stem}.jpg"
                try:
                    self._convert_heic(image_path, temp_path)
                    image_path = temp_path
                except Exception as e:
                    self.logger.error(f"Failed to convert HEIC to JPEG: {str(e)}")
                    return "unknown"

            try:
                # Open image with PIL
                with Image.open(image_path) as img:
                    # Basic heuristics for now - can be enhanced with ML later
                    width, height = img.size
                    aspect_ratio = width / height
                    
                    # Screenshots often have standard display ratios
                    if 1.3 <= aspect_ratio <= 1.8:
                        return "screenshot"
                    
                    # Photos often have 4:3 or 3:2 ratios
                    if 1.2 <= aspect_ratio <= 1.5:
                        return "photograph"
                    
                    return "diagram"
                    
            except Exception as e:
                self.logger.error(f"Failed to classify image: {str(e)}")
                return "unknown"
                
        finally:
            # Clean up temporary file if we created one
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                    temp_path.parent.rmdir()
                except Exception:
                    pass

    def _write_markdown(self, markdown_path: Path, title: str, image_path: Path, context: str, image_type: str) -> None:
        """Write markdown file for image with context.
        
        Args:
            markdown_path: Path to write markdown file.
            title: Title for markdown file.
            image_path: Path to image file.
            context: Image context from vision API.
            image_type: Classified image type.
        """
        # Get relative path from markdown to image
        rel_image_path = self._get_relative_path(markdown_path, image_path)
        
        # Create markdown content based on image type
        if image_type == "screenshot":
            content = f"""# {title}

## Screenshot Context
{context}

![Screenshot: {title}]({rel_image_path})
"""
        elif image_type == "photograph":
            content = f"""# {title}

## Image Description
{context}

![Photo: {title}]({rel_image_path})
"""
        else:  # diagram or unknown
            content = f"""# {title}

## Content Analysis
{context}

![{title}]({rel_image_path})
"""
        
        # Write markdown file using safe write method
        self._safe_write_file(markdown_path, content)

    async def process_impl(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: DocumentMetadata,
    ) -> Optional[DocumentMetadata]:
        """Process an image file.
        
        Args:
            file_path: Path to image file.
            output_dir: Directory to write output files.
            metadata: Document metadata.
            
        Returns:
            Document metadata.
        """
        try:
            # Create output directory
            output_dir = Path(str(output_dir))
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create markdown file
            markdown_path = output_dir / f"{file_path.stem}.parsed.md"
            
            # Get image context
            try:
                context = await self._get_image_context(file_path)
            except Exception as e:
                self.logger.error(f"Failed to get image context for {file_path.name}: {str(e)}")
                context = "Error getting image context. Please try again later."
            
            # Get image type
            image_type = self._classify_image_type(file_path)
            
            # Write markdown file with context, reference to original, and image type
            self._write_markdown(markdown_path, file_path.stem, file_path, context, image_type)
            
            # Update metadata
            metadata.title = file_path.stem
            metadata.metadata['original_path'] = str(file_path)
            metadata.metadata['context'] = context
            metadata.processed = True
            metadata.add_output_file(markdown_path)
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to process image {file_path}: {str(e)}")
            return None 