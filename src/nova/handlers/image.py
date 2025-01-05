"""Image file handler."""

# Standard library
import base64
import io
import mimetypes
import os
from pathlib import Path
from typing import Dict, List, Optional, Union

# External dependencies
import cairosvg
import pillow_heif
from openai import OpenAI
from PIL import Image

# Internal imports
from ..config.manager import ConfigManager
from ..core.markdown import MarkdownWriter
from ..models.document import DocumentMetadata
from .base import BaseHandler, ProcessingResult, ProcessingStatus


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
        os.environ["PILLOW_CACHE_DIR"] = str(
            Path(self.config.processing_dir) / "image_cache"
        )

        # Register HEIF format with Pillow
        pillow_heif.register_heif_opener()

        # Initialize OpenAI client if API key is configured
        self.vision_client = None
        try:
            if self.config.apis and self.config.apis.openai:
                self.logger.debug("Found OpenAI config")
                self.logger.debug(f"Raw API key: {self.config.apis.openai.api_key}")
                api_key = self.config.apis.openai.get_key()
                self.logger.debug(f"Processed API key: {api_key}")
                self.logger.debug(
                    f"API key valid: {self.config.apis.openai.has_valid_key}"
                )
                if api_key:
                    self.vision_client = OpenAI(api_key=api_key)
                    self.logger.info("OpenAI vision client initialized successfully")
                else:
                    self.logger.warning(
                        "OpenAI API key not configured, image descriptions will be disabled"
                    )
            else:
                self.logger.warning(
                    "OpenAI API key not configured, image descriptions will be disabled"
                )
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {str(e)}")

    def _encode_image(self, file_path: Path) -> str:
        """Encode image file as base64.

        Args:
            file_path: Path to image file.

        Returns:
            Base64 encoded image data.
        """
        try:
            # Handle SVG files by converting to PNG first
            if file_path.suffix.lower() == ".svg":
                # Create a temporary PNG file
                temp_png = file_path.parent / f"{file_path.stem}.temp.png"
                try:
                    # Convert SVG to PNG
                    cairosvg.svg2png(url=str(file_path), write_to=str(temp_png))
                    # Read the PNG file and encode it
                    with open(temp_png, "rb") as f:
                        png_data = f.read()
                    return base64.b64encode(png_data).decode("utf-8")
                finally:
                    # Clean up temporary file
                    if temp_png.exists():
                        temp_png.unlink()

            # Handle other image formats
            with Image.open(file_path) as img:
                # Convert to RGB if needed (e.g., for HEIC)
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGB")

                # Save as JPEG in memory
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=85)
                img_bytes = buffer.getvalue()

                return base64.b64encode(img_bytes).decode("utf-8")
        except Exception as e:
            self.logger.error(f"Failed to encode image {file_path}: {str(e)}")
            raise

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
            # Validate image file
            try:
                if file_path.suffix.lower() == ".svg":
                    # For SVG files, try to read and parse with cairosvg
                    try:
                        # Create a temporary PNG file to verify SVG is valid
                        temp_png = file_path.parent / f"{file_path.stem}.temp.png"
                        try:
                            cairosvg.svg2png(url=str(file_path), write_to=str(temp_png))
                        finally:
                            # Clean up temporary file
                            if temp_png.exists():
                                temp_png.unlink()
                    except Exception as e:
                        raise ValueError(f"Invalid SVG file: {str(e)}")
                else:
                    # For other image types, use PIL
                    with Image.open(file_path) as img:
                        img.verify()
            except Exception as e:
                error_msg = f"Invalid image file {file_path}: {str(e)}"
                self.logger.error(error_msg)
                metadata.add_error(self.name, error_msg)
                metadata.processed = False
                return metadata

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
                                        "text": "Please describe this image in detail.",
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{base64_image}"
                                        },
                                    },
                                ],
                            }
                        ],
                        max_tokens=300,
                    )

                    description = response.choices[0].message.content

                except Exception as e:
                    self.logger.error(f"Failed to generate image description: {str(e)}")
                    description = "Failed to generate image description"
            else:
                description = (
                    "Failed to generate image description: OpenAI API not configured"
                )

            # Update metadata
            metadata.title = file_path.stem
            metadata.processed = True
            metadata.metadata.update(
                {
                    "description": description,
                    "file_type": mimetypes.guess_type(file_path)[0]
                    or f"image/{file_path.suffix.lstrip('.').lower()}",
                }
            )

            # Create a unique marker for the image
            image_marker = f"[ATTACH:IMAGE:{file_path.stem}]"

            # Write markdown using MarkdownWriter
            markdown_content = self.markdown_writer.write_document(
                title=metadata.title,
                content=f"!{image_marker}\n\n{description}",
                metadata=metadata.metadata,
                file_path=file_path,
                output_path=output_path,
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
            return metadata
