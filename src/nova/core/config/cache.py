"""Cache configuration classes."""

from typing import Dict, Optional, Annotated
from pydantic import BaseModel, Field, ConfigDict

class CacheConfig(BaseModel):
    """Cache configuration."""
    enabled: bool = True
    max_size: Annotated[int, Field(ge=0)] = 1000
    ttl_seconds: Annotated[int, Field(ge=0)] = 3600
    
    model_config = {
        "extra": "forbid"
    } 