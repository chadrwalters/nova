"""Pipeline phase implementation."""

from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

from nova.core.utils.monitoring import MonitoringManager
from nova.core.models.result import ProcessingResult
from nova.core.errors import ValidationError


@dataclass
class PipelinePhase:
    """Represents a pipeline processing phase."""
    
    name: str
    config: Dict[str, Any]
    input_dir: Path
    output_dir: Path
    temp_dir: Path
    processor: Any
    monitor: MonitoringManager
    
    def __post_init__(self):
        """Validate phase configuration after initialization."""
        self._validate_config()
        
    def _validate_config(self) -> None:
        """Validate phase configuration.
        
        Raises:
            ValidationError: If configuration is invalid
        """
        if not self.name:
            raise ValidationError("Phase name is required")
            
        if not self.input_dir:
            raise ValidationError("Input directory is required")
            
        if not self.output_dir:
            raise ValidationError("Output directory is required")
            
        if not self.temp_dir:
            raise ValidationError("Temporary directory is required")
            
        if not self.processor:
            raise ValidationError("Processor is required")
            
    async def process(self, input_files: list[Path]) -> ProcessingResult:
        """Process input files.
        
        Args:
            input_files: List of input files to process
            
        Returns:
            Processing result
        """
        result = ProcessingResult()
        
        try:
            # Start monitoring
            self.monitor.start_phase(self.name)
            
            # Process files
            result = await self.processor.process(
                input_files=input_files,
                input_dir=self.input_dir,
                output_dir=self.output_dir,
                temp_dir=self.temp_dir,
                config=self.config
            )
            
        except Exception as e:
            result.add_error(str(e))
            
        finally:
            # Stop monitoring
            self.monitor.end_phase(self.name)
            
        return result
        
    async def cleanup(self) -> None:
        """Clean up phase resources."""
        if hasattr(self.processor, "cleanup"):
            await self.processor.cleanup() 