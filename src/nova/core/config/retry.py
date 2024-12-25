"""Retry configuration classes."""

from typing import Dict, Optional, List, Annotated
from pydantic import BaseModel, Field, ConfigDict

class RetryConfig(BaseModel):
    """Retry configuration."""
    max_retries: Annotated[int, Field(ge=0)] = 3
    delay_between_retries: Annotated[int, Field(ge=0)] = 1
    backoff_factor: Annotated[float, Field(ge=1.0)] = 2.0
    retry_on_errors: List[str] = ["timeout", "connection_error"]
    
    model_config = {
        "extra": "forbid"
    } 