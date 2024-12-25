"""Logging configuration classes."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict

class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    handlers: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "default"
            }
        },
        description="Logging handler configurations"
    )
    file: Optional[str] = Field(
        default=None,
        description="Optional log file path"
    )
    use_rich: bool = Field(
        default=True,
        description="Whether to use rich formatting for console output"
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra='forbid'
    ) 