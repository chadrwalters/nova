"""Pipeline configuration."""

from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field, model_validator, ConfigDict


class ProcessorConfig(BaseModel):
    """Processor configuration."""
    name: str
    description: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)
    components: Dict[str, Any] = Field(default_factory=dict)
    output_dir: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra='allow'
    )


class PipelineConfig(BaseModel):
    """Pipeline configuration."""
    input_dir: str
    output_dir: str
    processing_dir: str
    temp_dir: str
    phases: Dict[str, ProcessorConfig]
    cache_dir: Optional[str] = None
    log_level: str = "INFO"
    options: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra='allow'
    )

    @model_validator(mode='before')
    @classmethod
    def validate_config(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration before model creation.
        
        Args:
            values: Configuration values
            
        Returns:
            Validated configuration values
        """
        if not isinstance(values, dict):
            values = dict(values)

        # Extract paths from nested structure if present
        if 'paths' in values:
            paths = values.pop('paths')
            values.update(paths)

        # Convert phases list to dictionary if needed
        if 'phases' in values and isinstance(values['phases'], list):
            phases = {}
            for phase in values['phases']:
                if isinstance(phase, dict):
                    name = phase.pop('name', None)
                    if name:
                        phases[name] = phase
            values['phases'] = phases

        # Ensure required paths are present
        required_paths = ['input_dir', 'output_dir', 'processing_dir', 'temp_dir']
        for path in required_paths:
            if path not in values:
                values[path] = str(Path.cwd() / path.replace('_dir', ''))

        return values

    def get_input_dir(self) -> Path:
        """Get input directory path.
        
        Returns:
            Input directory path
        """
        return Path(self.input_dir).expanduser().resolve()

    def get_output_dir(self) -> Path:
        """Get output directory path.
        
        Returns:
            Output directory path
        """
        return Path(self.output_dir).expanduser().resolve()

    def get_processing_dir(self) -> Path:
        """Get processing directory path.
        
        Returns:
            Processing directory path
        """
        return Path(self.processing_dir).expanduser().resolve()

    def get_temp_dir(self) -> Path:
        """Get temporary directory path.
        
        Returns:
            Temporary directory path
        """
        return Path(self.temp_dir).expanduser().resolve()

    def get_cache_dir(self) -> Optional[Path]:
        """Get cache directory path.
        
        Returns:
            Cache directory path or None if not set
        """
        if self.cache_dir:
            return Path(self.cache_dir).expanduser().resolve()
        return None

    @classmethod
    def from_config(cls, config: Union[Dict[str, Any], str, Path]) -> 'PipelineConfig':
        """Create pipeline configuration from dictionary or file.
        
        Args:
            config: Configuration dictionary or path to configuration file
            
        Returns:
            Pipeline configuration
        """
        if isinstance(config, (str, Path)):
            config = cls._load_config_file(config)
        return cls(**config)

    @staticmethod
    def _load_config_file(path: Union[str, Path]) -> Dict[str, Any]:
        """Load configuration from file.
        
        Args:
            path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        path = Path(path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        if path.suffix == '.json':
            import json
            with path.open('r') as f:
                return json.load(f)
        elif path.suffix in ['.yaml', '.yml']:
            import yaml
            with path.open('r') as f:
                return yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported configuration file format: {path.suffix}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.
        
        Returns:
            Configuration dictionary
        """
        return self.model_dump() 