from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field

class LoggingConfig(BaseModel):
    """Basic logging configuration."""
    level: str = Field(default="INFO")
    format: str = Field(default="json")
    file: str = Field(default="")
    filter_binary: bool = Field(default=True)
    max_binary_length: int = Field(default=100)

    class Config:
        arbitrary_types_allowed = True

class ErrorSeverity(str, Enum):
    """Error severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    
    def to_logging_level(self) -> int:
        """Convert severity to logging level."""
        import logging
        return {
            self.CRITICAL: logging.CRITICAL,
            self.ERROR: logging.ERROR,
            self.WARNING: logging.WARNING,
            self.INFO: logging.INFO
        }[self]