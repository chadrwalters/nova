"""Image file handler."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Union
from openai import OpenAI
import base64
from PIL import Image
import io
import pillow_heif
import cairosvg

from ..models.document import DocumentMetadata
from .base import BaseHandler, ProcessingStatus, ProcessingResult
from ..config.manager import ConfigManager
from ..core.markdown import MarkdownWriter


class ImageHandler(BaseHandler):
    """Handler for image files."""
    
    name = "image"
    version = "0.1.0"
    file_types = ["jpg", "jpeg", "png", "heic", "svg"]
    
    def __init__(self, config: ConfigManager) -> None:
        """Initialize image handler.
        
        Args:
            config: Nova configuration manager.
        """
        super().__init__(config)
        self.markdown_writer = MarkdownWriter()
        
        # Set PIL cache directory to be within processing directory
        os.environ['PILLOW_CACHE_DIR'] = str(Path(self.config.processing_dir) / "image_cache")
        
        # Register HEIF format with Pillow
        pillow_heif.register_heif_opener()
        
        # Initialize OpenAI client if API key is configured
        self.vision_client = None
        if config.config.apis and config.config.apis.openai and config.config.apis.openai.api_key:
            self.vision_client = OpenAI(api_key=config.config.apis.openai.api_key)
        
    def _encode_image(self, file_path: Path) -> str:
        """Encode image file as base64.
        
        Args:
            file_path: Path to image file.
            
        Returns:
            Base64 encoded image data.
        """
        # Handle SVG files by converting to PNG first
        if file_path.suffix.lower() == '.svg':
            png_data = cairosvg.svg2png(url=str(file_path))
            return base64.b64encode(png_data).decode('utf-8')
            
        # Handle other image formats
        with Image.open(file_path) as img:
            # Convert to RGB if needed (e.g., for HEIC)
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
            
            # Save as JPEG in memory
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=85)
            img_byte_arr = img_byte_arr.getvalue()
            
            return base64.b64encode(img_byte_arr).decode('utf-8')
            
    async def process_file_impl(
        self,
        file_path: Path,
        output_path: Path,
        metadata: DocumentMetadata,
    ) -> Optional[DocumentMetadata]:
        """Process an image file.
        
        Args:
            file_path: Path to image file.
            output_path: Path to write output.
            metadata: Document metadata.
            
        Returns:
            Document metadata.
        """
        try:
            # Generate image description if vision client is available
            description = ""
            if self.vision_client:
                try:
                    # Encode image
                    base64_image = self._encode_image(file_path)
                    
                    # Call Vision API
                    response = self.vision_client.chat.completions.create(
                        model="gpt-4o",
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
                        max_tokens=300
                    )
                    
                    description = response.choices[0].message.content
                    
                except Exception as e:
                    self.logger.error(f"Failed to generate image description: {str(e)}")
                    description = "Failed to generate image description"
            else:
                description = "Failed to generate image description - no vision API configured"
            
            # Update metadata
            metadata.title = file_path.stem
            metadata.processed = True
            metadata.metadata.update({
                'description': description,
                'file_type': file_path.suffix.lstrip('.').upper()
            })
            
            # Write markdown using MarkdownWriter
            markdown_content = self.markdown_writer.write_document(
                title=metadata.title,
                content=f"![{metadata.title}]({file_path})\n\n{description}",
                metadata=metadata.metadata,
                file_path=file_path,
                output_path=output_path
            )
            
            # Write the file
            self._safe_write_file(output_path, markdown_content)
            
            metadata.add_output_file(output_path)
            return metadata
            
        except Exception as e:
            error_msg = f"Failed to process image {file_path}: {str(e)}"
            self.logger.error(error_msg)
            if metadata:
                metadata.add_error(self.name, error_msg)
                metadata.processed = False
            return None 