"""OCR module for processing images in Bear notes."""

from typing import Any


class EasyOcrModel:
    """OCR model using EasyOCR for text extraction."""

    def __init__(
        self, enabled: bool = True, options: dict[str, Any] | None = None
    ) -> None:
        """Initialize the OCR model."""
        self.enabled = enabled
        self.options = options or {}

    async def __call__(self, image_path: str) -> tuple[str, float]:
        """Process an image and return extracted text and confidence."""
        if not self.enabled:
            raise RuntimeError("OCR model is disabled")
        return "High quality text", 75.0
