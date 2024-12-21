from dataclasses import dataclass
from typing import Optional

@dataclass
class ImageMetadata:
    """Metadata for a processed image."""
    original_path: str
    processed_path: str
    width: int
    height: int
    format: str
    size: int
    description: Optional[str] = None
    processing_time: float = 0.0 