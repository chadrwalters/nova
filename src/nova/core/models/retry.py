"""Retry configuration model."""

from typing import List, Annotated
from pydantic import BaseModel, Field

class RetryConfig(BaseModel):
    """Retry configuration."""
    max_retries: Annotated[int, Field(ge=0)] = 3
    delay_between_retries: Annotated[int, Field(ge=0)] = 1
    backoff_factor: Annotated[float, Field(ge=1.0)] = 2.0
    retry_on_errors: List[str] = ["timeout", "connection_error"]

    model_config = {
        "validate_assignment": True,
        "extra": "forbid"
    } 