"""Configuration management for Nova Document Processor."""

import os
from pathlib import Path
import yaml

from .models import NovaConfig
from .logging import get_logger

logger = get_logger(__name__)

def load_config() -> NovaConfig:
    """Load configuration from default config file."""
    # First try NOVA_CONFIG_DIR environment variable
    config_dir = os.getenv('NOVA_CONFIG_DIR')
    if config_dir:
        config_path = Path(config_dir) / 'default_config.yaml'
    else:
        # Fall back to config directory in project root
        config_path = Path(__file__).parent.parent.parent / 'config' / 'default_config.yaml'
    
    if not config_path.exists():
        logger.warning(f"Config file not found at {config_path}, using defaults")
        return NovaConfig()
        
    try:
        with open(config_path) as f:
            config_data = yaml.safe_load(f)
        return NovaConfig.model_validate(config_data)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return NovaConfig()

# ... rest of config classes ...