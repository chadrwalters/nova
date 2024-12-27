"""Configuration management and utilities."""

import os
from pathlib import Path
from typing import Optional, Dict, Any, Union, List

import yaml
from pydantic import BaseModel, Field, ConfigDict

from nova.core.errors import ConfigurationError


class BaseConfig:
    """Base class for configuration objects."""
    
    def __init__(self, **kwargs) -> None:
        """Initialize configuration.
        
        Args:
            **kwargs: Configuration options
        """
        self._config = kwargs
        
    def __getattr__(self, name: str) -> Any:
        """Get configuration option.
        
        Args:
            name: Option name
            
        Returns:
            Option value
            
        Raises:
            AttributeError: If option does not exist
        """
        if name in self._config:
            return self._config[name]
        raise AttributeError(f"Configuration option not found: {name}")
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration option with default.
        
        Args:
            key: Option name
            default: Default value
            
        Returns:
            Option value or default
        """
        return self._config.get(key, default)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.
        
        Returns:
            Configuration dictionary
        """
        return dict(self._config)


class ProcessorConfig(BaseModel):
    """Base configuration for a processor."""
    name: str
    input_dir: Optional[str] = None
    output_dir: str
    processor: str
    components: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None
    
    def __init__(self, **data):
        """Initialize processor configuration.
        
        Args:
            **data: Configuration data
        """
        # Convert PosixPath to string for input_dir and output_dir
        if 'input_dir' in data and isinstance(data['input_dir'], Path):
            data['input_dir'] = str(data['input_dir'])
        if 'output_dir' in data and isinstance(data['output_dir'], Path):
            data['output_dir'] = str(data['output_dir'])
        super().__init__(**data)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.
        
        Returns:
            Configuration dictionary
        """
        return {
            'name': self.name,
            'input_dir': self.input_dir,
            'output_dir': self.output_dir,
            'processor': self.processor,
            'components': self.components,
            'description': self.description
        }


class PipelineConfig(BaseModel):
    """Configuration for the document processing pipeline."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    paths: Dict[str, str] = Field(default_factory=dict)
    phases: Dict[str, ProcessorConfig] = Field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration option with default.
        
        Args:
            key: Option name
            default: Default value
            
        Returns:
            Option value or default
        """
        data = self.model_dump()
        return data.get(key, default)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.
        
        Returns:
            Configuration dictionary
        """
        return {
            'paths': self.paths,
            'phases': {name: phase.to_dict() for name, phase in self.phases.items()}
        }
        
    @classmethod
    def load(cls, config_path: Optional[Union[str, Path]] = None) -> 'PipelineConfig':
        """Load configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            PipelineConfig instance
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            if not config_path:
                config_path = os.environ.get('NOVA_CONFIG_PATH', 'config/pipeline_config.yaml')
                
            config_path = Path(config_path)
            if not config_path.exists():
                raise ConfigurationError(f"Configuration file not found: {config_path}")
                
            with open(config_path) as f:
                config_data = yaml.safe_load(f)
                
            # Extract pipeline configuration
            if 'pipeline' in config_data:
                config_data = config_data['pipeline']
                
            return cls(**config_data)
            
        except Exception as e:
            raise ConfigurationError(f"Error loading configuration: {str(e)}")
