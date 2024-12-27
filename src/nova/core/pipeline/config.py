"""Pipeline configuration."""

from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from nova.core.errors import ValidationError


@dataclass
class PhaseConfig:
    """Pipeline phase configuration."""
    
    name: str
    description: str
    processor: str
    output_dir: Path
    components: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    timing: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    monitoring: Dict[str, Any] = field(default_factory=dict)
    error_handling: Dict[str, Any] = field(default_factory=dict)
    cache: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_config()
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        if key == "dependencies":
            return self.dependencies
        elif key == "components":
            return self.components
        elif key == "description":
            return self.description
        elif key == "output_dir":
            return str(self.output_dir)
        elif key == "processor":
            return self.processor
        elif key == "timing":
            return self.timing
        elif key == "metrics":
            return self.metrics
        elif key == "monitoring":
            return self.monitoring
        elif key == "error_handling":
            return self.error_handling
        elif key == "cache":
            return self.cache
        return default
        
    def _validate_config(self) -> None:
        """Validate phase configuration.
        
        Raises:
            ValidationError: If configuration is invalid
        """
        if not self.name:
            raise ValidationError("Phase name is required")
            
        if not self.description:
            raise ValidationError("Phase description is required")
            
        if not self.processor:
            raise ValidationError("Phase processor is required")
            
        if not self.output_dir:
            raise ValidationError("Phase output directory is required")
            
        # Validate components
        if not isinstance(self.components, dict):
            raise ValidationError("Invalid components configuration")
            
        # Validate dependencies
        if not isinstance(self.dependencies, list):
            raise ValidationError("Invalid dependencies configuration")
            
        # Validate timing
        if not isinstance(self.timing, dict):
            raise ValidationError("Invalid timing configuration")
            
        # Validate metrics
        if not isinstance(self.metrics, dict):
            raise ValidationError("Invalid metrics configuration")
            
        # Validate monitoring
        if not isinstance(self.monitoring, dict):
            raise ValidationError("Invalid monitoring configuration")
            
        # Validate error handling
        if not isinstance(self.error_handling, dict):
            raise ValidationError("Invalid error handling configuration")
            
        # Validate cache
        if not isinstance(self.cache, dict):
            raise ValidationError("Invalid cache configuration")
            

@dataclass
class PipelineConfig:
    """Pipeline configuration."""
    
    input_dir: Path
    output_dir: Path
    temp_dir: Path
    phases: Dict[str, PhaseConfig]
    timing: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    monitoring: Dict[str, Any] = field(default_factory=dict)
    error_handling: Dict[str, Any] = field(default_factory=dict)
    cache: Dict[str, Any] = field(default_factory=dict)
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize pipeline configuration.
        
        Args:
            config: Pipeline configuration dictionary
            
        Raises:
            ValidationError: If configuration is invalid
        """
        self._validate_config(config)
        
        # Initialize attributes
        self.input_dir = self._resolve_path(config["input_dir"])
        self.output_dir = self._resolve_path(config["output_dir"])
        self.temp_dir = self._resolve_path(config["temp_dir"])
        
        # Initialize phases
        self.phases = {}
        for phase_name, phase_config in config["phases"].items():
            if isinstance(phase_config, str):
                # Handle string phase configs (e.g. "PHASE1: PHASE2")
                dependencies = [dep.strip() for dep in phase_config.split(":")]
                phase_config = {
                    "name": phase_name,
                    "description": f"Phase {phase_name}",
                    "processor": "DummyProcessor",
                    "output_dir": self.output_dir / phase_name.lower(),
                    "dependencies": dependencies[1:] if len(dependencies) > 1 else []
                }
                
            self.phases[phase_name] = PhaseConfig(
                name=phase_name,
                description=phase_config["description"],
                processor=phase_config["processor"],
                output_dir=Path(phase_config["output_dir"]),
                components=phase_config.get("components", {}),
                dependencies=phase_config.get("dependencies", []),
                timing=phase_config.get("timing", {}),
                metrics=phase_config.get("metrics", {}),
                monitoring=phase_config.get("monitoring", {}),
                error_handling=phase_config.get("error_handling", {}),
                cache=phase_config.get("cache", {})
            )
            
        # Initialize components
        self.timing = config.get("timing", {})
        self.metrics = config.get("metrics", {})
        self.monitoring = config.get("monitoring", {})
        self.error_handling = config.get("error_handling", {})
        self.cache = config.get("cache", {})
        
    def get_phase_dependencies(self, phase_name: str) -> List[str]:
        """Get phase dependencies.
        
        Args:
            phase_name: Phase name
            
        Returns:
            List of dependency phase names
            
        Raises:
            ValidationError: If phase not found
        """
        if phase_name not in self.phases:
            raise ValidationError(f"Unknown phase: {phase_name}")
            
        return self.phases[phase_name].dependencies
        
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate pipeline configuration.
        
        Args:
            config: Pipeline configuration dictionary
            
        Raises:
            ValidationError: If configuration is invalid
        """
        # Validate required keys
        required_keys = ["input_dir", "output_dir", "temp_dir", "phases"]
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            raise ValidationError(f"Missing required key: {missing_keys[0]}")
            
        # Validate phases
        phases = config["phases"]
        if not isinstance(phases, dict):
            raise ValidationError("Invalid phases configuration")
            
        if not phases:
            raise ValidationError("No phases defined")
            
        # Validate phase dependencies
        self._validate_phase_dependencies(phases)
        
    def _validate_phase_dependencies(self, phases: Dict[str, Any]) -> None:
        """Validate phase dependencies.
        
        Args:
            phases: Phase configuration dictionary
            
        Raises:
            ValidationError: If dependencies are invalid
        """
        # Build dependency graph
        dependencies = {}
        for phase_name, phase_config in phases.items():
            if isinstance(phase_config, str):
                # Handle string phase configs (e.g. "PHASE1: PHASE2")
                deps = [dep.strip() for dep in phase_config.split(":")]
                dependencies[phase_name] = deps[1:] if len(deps) > 1 else []
            else:
                dependencies[phase_name] = phase_config.get("dependencies", [])
                
        # Validate dependencies exist
        for phase_name, deps in dependencies.items():
            for dep in deps:
                if dep not in phases:
                    raise ValidationError(f"Unknown dependency: {dep}")
                    
        # Check for circular dependencies
        visited = set()
        path = []
        
        def visit(phase: str) -> None:
            if phase in path:
                raise ValidationError("Circular dependency detected")
                
            if phase in visited:
                return
                
            visited.add(phase)
            path.append(phase)
            
            for dep in dependencies[phase]:
                visit(dep)
                
            path.pop()
            
        for phase in dependencies:
            visit(phase)
            
    def _resolve_path(self, path: str) -> Path:
        """Resolve path, handling environment variables and symlinks.
        
        Args:
            path: Path to resolve
            
        Returns:
            Resolved path
        """
        # Expand environment variables
        path = self._expand_env_vars(path)
        
        # Convert to Path and resolve
        path = Path(path).expanduser()
        if path.is_symlink():
            return path.resolve().resolve()
        if path.is_absolute():
            return path
        return path.resolve()
        
    def _expand_env_vars(self, value: str) -> str:
        """Expand environment variables in string value.
        
        Args:
            value: String value potentially containing environment variables
            
        Returns:
            String with environment variables expanded
            
        Raises:
            ValidationError: If environment variable is not found
        """
        import os
        import re
        
        pattern = r'\${([^}]+)}'
        matches = re.finditer(pattern, value)
        
        result = value
        for match in matches:
            env_var = match.group(1)
            env_value = os.environ.get(env_var)
            
            if env_value is None:
                raise ValidationError(f"Environment variable not found: {env_var}")
                
            result = result.replace(f"${{{env_var}}}", env_value)
            
        return result 