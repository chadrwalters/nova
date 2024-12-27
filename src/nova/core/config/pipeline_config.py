"""Pipeline configuration."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Type

from nova.core.errors import ValidationError


@dataclass
class PhaseConfig:
    """Configuration for a pipeline phase."""
    
    name: str
    config: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    description: str = ""
    processor: Optional[Type] = None
    output_dir: Optional[Path] = None
    components: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    timing: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    monitoring: Dict[str, Any] = field(default_factory=dict)
    error_handling: Dict[str, Any] = field(default_factory=dict)
    cache: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize after dataclass creation."""
        self.description = self.config.get("description", "")
        self.processor = self.config.get("processor")
        self.components = self.config.get("components", {})
        self.output_dir = Path(self.config["output_dir"]) if "output_dir" in self.config else None
        self.timing = self.config.get("timing", {})
        self.metrics = self.config.get("metrics", {})
        self.monitoring = self.config.get("monitoring", {})
        self.error_handling = self.config.get("error_handling", {})
        self.cache = self.config.get("cache", {})
    
    def get_output_dir(self) -> Path:
        """Get phase output directory.
        
        Returns:
            Output directory path
            
        Raises:
            ValidationError: If output directory not configured
        """
        if not self.output_dir:
            raise ValidationError(f"No output directory configured for phase {self.name}")
            
        # Resolve environment variables
        output_dir = str(self.output_dir)
        if "${" in output_dir:
            # Extract variable name between ${ and }
            start = output_dir.find("${")
            end = output_dir.find("}", start)
            if end == -1:
                raise ValidationError(f"Invalid environment variable syntax: {output_dir}")
                
            var_name = output_dir[start+2:end]
            if var_name not in os.environ:
                raise ValidationError(f"Environment variable not found: {var_name}")
                
            # Replace ${VAR} with value
            output_dir = output_dir[:start] + os.environ[var_name] + output_dir[end+1:]
            
        return Path(output_dir)
        
    def get_processor(self) -> Type:
        """Get phase processor class.
        
        Returns:
            Processor class
            
        Raises:
            ValidationError: If processor not configured
        """
        if not self.processor:
            raise ValidationError(f"No processor configured for phase {self.name}")
        return self.processor
        
    def get_dependencies(self) -> List[str]:
        """Get phase dependencies.
        
        Returns:
            List of phase names this phase depends on
        """
        return self.dependencies
        
    def validate(self) -> None:
        """Validate phase configuration.
        
        Raises:
            ValidationError: If configuration is invalid
        """
        # Validate processor first
        if "processor" not in self.config:
            raise ValidationError("Missing required key: processor")
            
        processor = self.get_processor()
        if not callable(processor):
            raise ValidationError(f"Processor must be callable: {processor}")
            
        # Validate other required keys
        required_keys = ["components", "output_dir"]
        for key in required_keys:
            if key not in self.config:
                raise ValidationError(f"Missing required key: {key}")
                
        # Validate output directory
        output_dir = self.get_output_dir()
        if not output_dir.parent.exists():
            raise ValidationError(f"Parent directory does not exist: {output_dir.parent}")


@dataclass
class PipelineConfig:
    """Pipeline configuration."""
    
    phases: Dict[str, PhaseConfig] = field(default_factory=dict)
    input_dir: Optional[Path] = None
    output_dir: Optional[Path] = None
    temp_dir: Optional[Path] = None
    timing: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    monitoring: Dict[str, Any] = field(default_factory=dict)
    error_handling: Dict[str, Any] = field(default_factory=dict)
    cache: Dict[str, Any] = field(default_factory=dict)
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize pipeline configuration.
        
        Args:
            config: Raw configuration dictionary
            
        Raises:
            ValidationError: If configuration is invalid
        """
        # Validate required keys
        required_keys = ["phases", "input_dir", "output_dir", "temp_dir"]
        for key in required_keys:
            if key not in config:
                raise ValidationError(f"Missing required key: {key}")
                
        # Initialize phases
        self.phases = {}
        for name, phase_config in config["phases"].items():
            dependencies = phase_config.get("dependencies", [])
            self.phases[name] = PhaseConfig(name, phase_config, dependencies)
            
        # Initialize directories
        self.input_dir = self._resolve_path(config["input_dir"])
        self.output_dir = self._resolve_path(config["output_dir"])
        self.temp_dir = self._resolve_path(config["temp_dir"])
        
        # Initialize optional attributes
        self.timing = config.get("timing", {})
        self.metrics = config.get("metrics", {})
        self.monitoring = config.get("monitoring", {})
        self.error_handling = config.get("error_handling", {})
        self.cache = config.get("cache", {})
        
        # Validate configuration
        self.validate()
        
    def _resolve_path(self, path: str) -> Path:
        """Resolve path with environment variable expansion.
        
        Args:
            path: Path string
            
        Returns:
            Resolved path
            
        Raises:
            ValidationError: If path is invalid or environment variable not found
        """
        if not path:
            raise ValidationError("No path specified")
            
        if not isinstance(path, (str, Path)):
            raise ValidationError("Invalid path type")
            
        # Expand environment variables
        if isinstance(path, str) and "${" in path:
            # Extract variable name between ${ and }
            start = path.find("${")
            end = path.find("}", start)
            if end == -1:
                raise ValidationError(f"Invalid environment variable syntax: {path}")
                
            var_name = path[start+2:end]
            if var_name not in os.environ:
                raise ValidationError(f"Environment variable not found: {var_name}")
                
            # Replace ${VAR} with value
            path = path[:start] + os.environ[var_name] + path[end+1:]
            
        # Convert to absolute path
        path = Path(path)
        if not path.is_absolute():
            path = Path.cwd() / path
            
        return path
        
    def get_phase_configs(self) -> Dict[str, PhaseConfig]:
        """Get phase configurations.
        
        Returns:
            Dictionary mapping phase names to configurations
        """
        return self.phases
        
    def get_phase_dependencies(self, phase_name: str) -> List[str]:
        """Get dependencies for a phase.
        
        Args:
            phase_name: Name of phase to get dependencies for
            
        Returns:
            List of phase names this phase depends on
            
        Raises:
            ValidationError: If phase not found
        """
        if phase_name not in self.phases:
            raise ValidationError(f"Unknown phase: {phase_name}")
        return self.phases[phase_name].get_dependencies()
        
    def validate(self) -> None:
        """Validate pipeline configuration.
        
        Raises:
            ValidationError: If configuration is invalid
        """
        # Validate phases exist
        if not self.phases:
            raise ValidationError("No phases configured")
            
        # Validate phase dependencies
        for name, phase in self.phases.items():
            for dep in phase.get_dependencies():
                if dep not in self.phases:
                    raise ValidationError(f"Unknown dependency {dep} for phase {name}")
                    
        # Validate directories
        if not self.input_dir.exists():
            raise ValidationError(f"Input directory does not exist: {self.input_dir}")
            
        if not self.output_dir.parent.exists():
            raise ValidationError(f"Parent of output directory does not exist: {self.output_dir.parent}")
            
        if not self.temp_dir.parent.exists():
            raise ValidationError(f"Parent of temp directory does not exist: {self.temp_dir.parent}")
            
        # Validate individual phases
        for phase in self.phases.values():
            phase.validate() 