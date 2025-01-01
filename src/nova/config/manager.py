"""Configuration manager for Nova."""
import os
from pathlib import Path
from typing import Optional, Union
import logging

import yaml

from nova.config.settings import NovaConfig, CacheConfig, PipelineConfig

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages configuration loading and access for Nova."""
    
    DEFAULT_CONFIG_PATH = Path(__file__).parent / "default.yaml"
    ENV_CONFIG_PATH = "NOVA_CONFIG_PATH"
    
    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        create_dirs: bool = True,
    ) -> None:
        """Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file. If not provided, will check
                environment variable NOVA_CONFIG_PATH, then fall back to default.
            create_dirs: Whether to create configured directories if they don't exist.
        """
        self.logger = logging.getLogger(__name__)
        self.config_path = self._resolve_config_path(config_path)
        self.logger.info(f"Loading config from: {self.config_path}")
        self.config = self._load_config()
        self.logger.info(f"Using input directory: {self.input_dir}")
        
        if create_dirs:
            self._create_directories()
    
    def _get_safe_path_str(self, file_path: Union[str, Path]) -> str:
        """Get safe string representation of path.
        
        Args:
            file_path: Path to convert.
            
        Returns:
            Safe string representation of path.
        """
        try:
            # Try to convert path to string normally
            return str(file_path)
        except UnicodeError:
            # If that fails, try to handle paths with non-UTF-8 characters
            return str(file_path).encode('utf-8', errors='replace').decode('utf-8')
    
    def _safe_path(self, path: Union[str, Path]) -> Path:
        """Convert path to Path object safely.
        
        Args:
            path: Path to convert.
            
        Returns:
            Path object.
        """
        if path is None:
            return None
            
        try:
            # If already a Path, convert to string first
            path_str = str(path)
            
            # Handle Windows encoding
            safe_str = path_str.encode('cp1252', errors='replace').decode('cp1252')
            
            # Expand environment variables and user paths
            safe_str = os.path.expandvars(os.path.expanduser(safe_str))
            
            # Convert back to Path
            return Path(safe_str)
        except Exception:
            # If all else fails, use the path as is
            return Path(path)
    
    def _resolve_config_path(self, config_path: Optional[Union[str, Path]] = None) -> Path:
        """Resolve configuration file path.
        
        Args:
            config_path: Path to configuration file.
            
        Returns:
            Resolved path to configuration file.
        """
        if config_path:
            return self._safe_path(config_path)
        
        env_path = os.environ.get(self.ENV_CONFIG_PATH)
        if env_path:
            return self._safe_path(env_path)
        
        return self._safe_path(self.DEFAULT_CONFIG_PATH)
    
    def _load_config(self) -> NovaConfig:
        """Load configuration from file.
        
        Returns:
            Loaded configuration.
            
        Raises:
            FileNotFoundError: If configuration file not found.
            ValueError: If configuration file is invalid.
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f) or {}
            
            # Ensure required sections exist
            if 'cache' not in config_dict:
                config_dict['cache'] = {}
            
            # Expand environment variables and user paths
            if 'base_dir' in config_dict:
                config_dict['base_dir'] = os.path.expandvars(os.path.expanduser(config_dict['base_dir']))
            if 'input_dir' in config_dict:
                config_dict['input_dir'] = os.path.expandvars(os.path.expanduser(config_dict['input_dir']))
            if 'output_dir' in config_dict:
                config_dict['output_dir'] = os.path.expandvars(os.path.expanduser(config_dict['output_dir']))
            if 'processing_dir' in config_dict:
                config_dict['processing_dir'] = os.path.expandvars(os.path.expanduser(config_dict['processing_dir']))
            if 'cache' in config_dict and 'dir' in config_dict['cache']:
                config_dict['cache']['dir'] = os.path.expandvars(os.path.expanduser(config_dict['cache']['dir']))
            
            # Expand environment variables in API configuration
            if 'apis' in config_dict:
                apis_config = config_dict['apis']
                if 'openai' in apis_config:
                    openai_config = apis_config['openai']
                    if 'api_key' in openai_config:
                        openai_config['api_key'] = os.path.expandvars(openai_config['api_key'])
                        if '${' in openai_config['api_key']:  # If still contains unexpanded variables
                            openai_config['api_key'] = None  # Set to None to trigger environment lookup
            
            # Convert paths to Path objects
            base_dir = os.path.expandvars(os.path.expanduser("${HOME}/Library/Mobile Documents/com~apple~CloudDocs"))
            config_dict['base_dir'] = self._safe_path(config_dict.get('base_dir', base_dir))
            config_dict['input_dir'] = self._safe_path(config_dict.get('input_dir', f"{base_dir}/_NovaInput"))
            config_dict['output_dir'] = self._safe_path(config_dict.get('output_dir', f"{base_dir}/_Nova"))
            config_dict['processing_dir'] = self._safe_path(config_dict.get('processing_dir', f"{base_dir}/_NovaProcessing"))
            
            # Ensure cache config
            cache_config = config_dict.get('cache', {})
            if 'dir' not in cache_config:
                cache_config['dir'] = f"{base_dir}/_NovaCache"
            cache_config['dir'] = self._safe_path(cache_config['dir'])
            
            # Set cache defaults
            if 'enabled' not in cache_config:
                cache_config['enabled'] = True
            if 'ttl' not in cache_config:
                cache_config['ttl'] = 3600
            elif isinstance(cache_config['ttl'], dict):
                # Convert legacy TTL dict to single value
                cache_config['ttl'] = 3600
            
            config_dict['cache'] = cache_config
            
            return NovaConfig(**config_dict)
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except Exception as e:
            raise ValueError(f"Invalid configuration file: {str(e)}")
    
    def _create_directories(self) -> None:
        """Create configured directories if they don't exist."""
        dirs = [
            self.base_dir,
            self.input_dir,
            self.output_dir,
            self.processing_dir,
            self.cache_dir,
        ]
        
        for dir_path in dirs:
            if dir_path:
                dir_path = self._safe_path(dir_path)
                logger.debug(f"Creating directory: {dir_path}")
                dir_path.mkdir(parents=True, exist_ok=True)
                if dir_path.exists():
                    logger.debug(f"Directory exists: {dir_path}")
                else:
                    logger.error(f"Failed to create directory: {dir_path}")
                    raise IOError(f"Failed to create directory: {dir_path}")
    
    def save_config(self, config_path: Optional[Union[str, Path]] = None) -> None:
        """Save current configuration to file.
        
        Args:
            config_path: Path to save configuration to. If not provided, will
                save to current config path.
        """
        path = Path(config_path) if config_path else self.config_path
        self.config.to_file(path)
    
    def update_config(self, config_data: dict) -> None:
        """Update configuration with new values.
        
        Args:
            config_data: Dictionary of configuration values to update.
        """
        # Create new config with updated values
        new_config = {
            **self.config.dict(),
            **config_data,
        }
        self.config = NovaConfig(**new_config)
    
    @property
    def base_dir(self) -> Path:
        """Get base directory path."""
        return self._safe_path(self.config.base_dir)
    
    @property
    def input_dir(self) -> Path:
        """Get input directory path."""
        return self._safe_path(self.config.input_dir)
    
    @property
    def output_dir(self) -> Path:
        """Get output directory path."""
        return self._safe_path(self.config.output_dir)
    
    @property
    def processing_dir(self) -> Path:
        """Get processing directory path."""
        return self._safe_path(self.config.processing_dir)
    
    @property
    def cache_dir(self) -> Path:
        """Get cache directory path."""
        return self._safe_path(self.config.cache.dir)
    
    @property
    def cache(self) -> CacheConfig:
        """Get cache configuration."""
        return self.config.cache

    @property
    def pipeline(self) -> PipelineConfig:
        """Get pipeline configuration."""
        return self.config.pipeline
        
    def __str__(self) -> str:
        """Get string representation of config manager."""
        return str(self.config)
        
    def __fspath__(self) -> str:
        """Return the file system path representation.
        
        This makes ConfigManager compatible with os.PathLike.
        """
        return str(self.input_dir) 