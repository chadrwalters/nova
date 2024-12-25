"""Processor configuration classes."""

from typing import Dict, Any, Optional, List
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict

class ProcessorConfig(BaseModel):
    """Base processor configuration."""
    enabled: bool = Field(default=True, description="Whether the processor is enabled")
    processor: str = Field(default="", description="Processor class name")
    input_dir: Optional[Path] = Field(default=None, description="Input directory")
    output_dir: Optional[Path] = Field(default=None, description="Output directory")
    options: Dict[str, Any] = Field(default_factory=dict, description="Processor options")

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    def __init__(self, **data):
        """Initialize processor configuration."""
        super().__init__(**data)
        
        # Convert output_dir to Path if it's a string
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)
        
        # Create output directory if it exists
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)