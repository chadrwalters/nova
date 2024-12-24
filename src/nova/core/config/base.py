"""Base configuration classes for Nova document processor."""

from pathlib import Path
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from pydantic import BaseModel, Field
import os

if TYPE_CHECKING:
    from ..pipeline.phase import PhaseType

class PathConfig(BaseModel):
    """Configuration for file paths."""
    
    base_dir: Path = Field(
        default=Path.cwd(),
        description="Base directory for all operations"
    )
    input_dir: Optional[Path] = Field(
        default=None,
        description="Input directory for files to process"
    )
    output_dir: Optional[Path] = Field(
        default=None,
        description="Output directory for processed files"
    )
    temp_dir: Optional[Path] = Field(
        default=None,
        description="Temporary directory for processing"
    )
    processing_dir: Optional[Path] = Field(
        default=None,
        description="Directory for intermediate processing"
    )
    
    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True
        
    def get_phase_dir(self, phase_type: Any) -> Optional[Path]:
        """Get directory for a specific phase.
        
        Args:
            phase_type: Type of phase
            
        Returns:
            Path to phase directory if found, None otherwise
        """
        # Get phase directory from environment
        phase_env_var = f"NOVA_PHASE_{phase_type.name}"
        phase_dir = os.getenv(phase_env_var)
        
        if phase_dir:
            return Path(phase_dir)
            
        # Fall back to processing_dir/phases/phase_name
        if self.processing_dir:
            return self.processing_dir / 'phases' / phase_type.name.lower()
            
        return None

class ProcessorConfig(BaseModel):
    """Configuration for a processor."""
    
    enabled: bool = Field(
        default=True,
        description="Whether the processor is enabled"
    )
    input_dir: Optional[Path] = Field(
        default=None,
        description="Input directory for this processor"
    )
    output_dir: Optional[Path] = Field(
        default=None,
        description="Output directory for this processor"
    )
    options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional processor options"
    )
    handlers: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Handler configurations"
    )
    
    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True

class HandlerConfig(BaseModel):
    """Configuration for a handler."""
    
    type: str = Field(
        ...,
        description="Handler type (module.class)"
    )
    enabled: bool = Field(
        default=True,
        description="Whether the handler is enabled"
    )
    options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Handler options"
    )
    
    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True

class PipelineConfig(BaseModel):
    """Configuration for the pipeline."""
    
    paths: PathConfig = Field(
        default_factory=PathConfig,
        description="Path configuration"
    )
    processors: Dict[str, ProcessorConfig] = Field(
        default_factory=dict,
        description="Processor configurations"
    )
    options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Pipeline options"
    )
    
    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True
    
    def get_processor_config(self, name: str) -> ProcessorConfig:
        """Get processor configuration.
        
        Args:
            name: Processor name
            
        Returns:
            Processor configuration
        """
        return self.processors.get(name, ProcessorConfig())
    
    def set_processor_config(self, name: str, config: ProcessorConfig) -> None:
        """Set processor configuration.
        
        Args:
            name: Processor name
            config: Processor configuration
        """
        self.processors[name] = config 