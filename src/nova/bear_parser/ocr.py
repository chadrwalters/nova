"""OCR module for processing images in Bear notes."""

from typing import Any


class EasyOcrModel:
    """EasyOcr model wrapper."""

    def __init__(self) -> None:
        """Initialize OCR model."""
        self._name = "gpt-4o"
        self._supported_formats = ["png", "jpg", "jpeg", "pdf", "tiff"]

    @property
    def name(self) -> str:
        """Get model name."""
        return self._name

    @property
    def supported_formats(self) -> list[str]:
        """Get supported formats."""
        return self._supported_formats

    def process_image(self, image_path: str) -> tuple[str, float, list[dict[str, Any]]]:
        """Process image with OCR.

        Args:
            image_path: Path to image file

        Returns:
            Tuple of (text, confidence, regions)
        """
        # TODO: Implement OCR processing
        return "test", 0.95, []

    async def __call__(
        self, image_path: str
    ) -> tuple[str, float, list[dict[str, Any]]]:
        """Process an image and return extracted text, confidence, and
        regions."""
        return self.process_image(image_path)
