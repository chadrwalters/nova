"""Shared models for Nova Document Processor."""

from enum import Enum
from typing import List
from pydantic import BaseModel, Field

class ErrorTolerance(str, Enum):
    """Error tolerance levels."""
    STRICT = "strict"
    LENIENT = "lenient"

class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO")
    format: str = Field(default="json")
    filter_binary: bool = Field(default=True)
    max_binary_length: int = Field(default=100) 