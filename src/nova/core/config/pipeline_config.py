"""Pipeline configuration management."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from nova.core.pipeline.phase_runner import PhaseRunner


@dataclass
class PhaseConfig:
    """Configuration for a pipeline phase."""
    name: str
    description: str
    output_dir: Path
    processor: Type[Any]
    components: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class PipelineConfig:
    """Configuration for document processing pipeline."""
    phases: List[PhaseConfig] = field(default_factory=list)
    timing: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'PipelineConfig':
        """Create pipeline configuration from dictionary.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            Pipeline configuration instance
        """
        # Extract pipeline section if it exists
        pipeline_config = config_dict.get("pipeline", config_dict)
        
        phases = []
        for phase_name, phase_config in pipeline_config.get("phases", {}).items():
            # Skip if phase config is not a dictionary
            if not isinstance(phase_config, dict):
                continue
                
            phases.append(PhaseConfig(
                name=phase_name,
                description=phase_config.get("description", ""),
                output_dir=Path(phase_config["output_dir"]),
                processor=phase_config["processor"],
                components=phase_config.get("components", {}),
                enabled=phase_config.get("enabled", True)
            ))
            
        return cls(
            phases=phases,
            timing=pipeline_config.get("timing", {}),
            metrics=pipeline_config.get("metrics", {})
        )
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.
        
        Returns:
            Configuration dictionary
        """
        return {
            "phases": {
                phase.name: {
                    "description": phase.description,
                    "output_dir": str(phase.output_dir),
                    "processor": phase.processor,
                    "components": phase.components,
                    "enabled": phase.enabled
                }
                for phase in self.phases
            },
            "timing": self.timing,
            "metrics": self.metrics
        }
        
    def get_phase_config(self, phase_name: str) -> Optional[PhaseConfig]:
        """Get configuration for a specific phase.
        
        Args:
            phase_name: Name of phase
            
        Returns:
            Phase configuration if found, None otherwise
        """
        for phase in self.phases:
            if phase.name == phase_name:
                return phase
        return None
        
    def get_enabled_phases(self) -> List[PhaseConfig]:
        """Get list of enabled phases.
        
        Returns:
            List of enabled phase configurations
        """
        return [phase for phase in self.phases if phase.enabled]
        
    def validate(self) -> None:
        """Validate pipeline configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate phases
        if not self.phases:
            raise ValueError("No phases configured")
            
        # Validate phase order
        phase_names = set()
        for phase in self.phases:
            if phase.name in phase_names:
                raise ValueError(f"Duplicate phase name: {phase.name}")
            phase_names.add(phase.name)
            
            # Validate phase configuration
            if not phase.processor:
                raise ValueError(f"No processor configured for phase {phase.name}")
                
            # Validate output directory
            if not phase.output_dir:
                raise ValueError(f"No output directory configured for phase {phase.name}")
                
        # Validate timing configuration
        if "phase_throughput_thresholds" in self.timing:
            for phase_name in self.timing["phase_throughput_thresholds"]:
                if phase_name not in phase_names:
                    raise ValueError(f"Invalid phase name in timing thresholds: {phase_name}")
                    
        # Validate metrics configuration
        if "counters" in self.metrics:
            for counter in self.metrics["counters"]:
                if not counter.startswith("phase_"):
                    continue
                phase_name = counter.split("_")[1]
                if phase_name not in phase_names:
                    raise ValueError(f"Invalid phase name in metrics counters: {phase_name}") 