"""Pipeline loader module."""

import os
from pathlib import Path
from typing import Dict, Any, Optional

import yaml

from nova.core.errors import ValidationError
from .config import PipelineConfig


class PipelineLoader:
    """Loader for pipeline configurations."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize pipeline loader."""
        self.config_path = config_path or os.getenv("NOVA_CONFIG_PATH")
        if not self.config_path:
            raise ValidationError("No configuration path specified")

    def load(self) -> PipelineConfig:
        """Load pipeline configuration."""
        config_path = Path(self.config_path)
        if not config_path.exists():
            raise ValidationError(f"Configuration file not found: {config_path}")

        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML configuration: {e}")
        except Exception as e:
            raise ValidationError(f"Error loading configuration: {e}")

        if not isinstance(config, dict):
            raise ValidationError("Invalid configuration format")

        # Expand environment variables
        config = self._expand_env_vars(config)

        return PipelineConfig(config)

    def _expand_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Expand environment variables in configuration."""
        if isinstance(config, dict):
            return {k: self._expand_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._expand_env_vars(v) for v in config]
        elif isinstance(config, str):
            return os.path.expandvars(config)
        return config 