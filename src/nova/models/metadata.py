"""Metadata models for Nova document processor."""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ImageMetadata(BaseModel):
    """Image metadata model."""
    
    source_path: str = Field(description="Path to source image file")
    format: str = Field(description="Image format (e.g., JPEG, PNG)")
    mode: str = Field(description="Image mode (e.g., RGB, RGBA)")
    size: tuple[int, int] = Field(description="Image dimensions (width, height)")
    info: Dict = Field(default_factory=dict, description="Additional image info")
    
    class Config:
        """Model configuration."""
        arbitrary_types_allowed = True
        json_encoders = {
            Path: str,
            datetime: lambda v: v.isoformat(),
        } 