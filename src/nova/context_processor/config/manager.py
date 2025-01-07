"""Configuration manager for Nova."""

# Standard library
import logging
import os
from pathlib import Path
from typing import Optional, Union

# External dependencies
import yaml

# Internal imports
from nova.context_processor.config.settings import APIConfig, CacheConfig, NovaConfig, PipelineConfig

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages configuration loading and access for Nova."""

    DEFAULT_CONFIG_PATH = Path(__file__).parent / "default.yaml"
    ENV_CONFIG_PATH = "NOVA_CONFIG_PATH"

    def __init__(
        self,
        config: Optional[Union[str, Path, NovaConfig]] = None,
        create_dirs: bool = True,
    ) -> None:
        """Initialize configuration manager.

        Args:
            config: Path to configuration file or NovaConfig instance. If not provided, will check
                environment variable NOVA_CONFIG_PATH, then fall back to default.
            create_dirs: Whether to create configured directories if they don't exist.
        """
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"Initializing ConfigManager with config: {config}")

        if isinstance(config, NovaConfig):
            self.config = config
            self.config_path = None
            self.logger.info(f"Using provided NovaConfig instance")
        else:
            self.config_path = self._resolve_config_path(config)
            self.logger.info(f"Config path resolved to: {self.config_path}")
            self.logger.info(f"Config path exists: {self.config_path.exists()}")
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
            return str(file_path).encode("utf-8", errors="replace").decode("utf-8")

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
            safe_str = path_str.encode("cp1252", errors="replace").decode("cp1252")

            # Only expand user paths (~ for home directory)
            safe_str = os.path.expanduser(safe_str)

            # Convert back to Path
            return Path(safe_str)
        except Exception:
            # If all else fails, use the path as is
            return Path(path)

    def _resolve_config_path(
        self, config_path: Optional[Union[str, Path]] = None
    ) -> Path:
        """Resolve configuration file path.

        Args:
            config_path: Path to configuration file.

        Returns:
            Resolved path to configuration file.
        """
        self.logger.debug(f"Resolving config path: {config_path}")
        
        # First check if a config path was provided
        if config_path:
            # Try multiple ways to resolve the path
            try:
                # First try: Direct Path conversion
                path = Path(config_path)
                self.logger.debug(f"Checking path: {path}")
                if path.exists():
                    self.logger.info(f"Using config file: {path}")
                    return path

                # Second try: Resolve the path
                resolved = path.resolve()
                self.logger.debug(f"Checking resolved path: {resolved}")
                if resolved.exists():
                    self.logger.info(f"Using config file: {resolved}")
                    return resolved

                # Third try: If not absolute, try relative to cwd
                if not path.is_absolute():
                    cwd_path = Path.cwd() / path
                    self.logger.debug(f"Checking relative to cwd: {cwd_path}")
                    if cwd_path.exists():
                        self.logger.info(f"Using config file: {cwd_path}")
                        return cwd_path

                # Fourth try: Expand user and resolve
                expanded = Path(os.path.expanduser(str(path))).resolve()
                self.logger.debug(f"Checking expanded path: {expanded}")
                if expanded.exists():
                    self.logger.info(f"Using config file: {expanded}")
                    return expanded

                self.logger.warning(f"Config file not found: {path}")
                self.logger.debug("Attempted paths:")
                self.logger.debug(f"  Direct: {path}")
                self.logger.debug(f"  Resolved: {resolved}")
                self.logger.debug(f"  CWD-relative: {Path.cwd() / path}")
                self.logger.debug(f"  User-expanded: {expanded}")
            except Exception as e:
                self.logger.warning(f"Error resolving config path: {e}")

        # Then check environment variable
        env_path = os.environ.get(self.ENV_CONFIG_PATH)
        if env_path:
            try:
                path = Path(env_path)
                self.logger.debug(f"Checking environment path: {path}")
                if path.exists():
                    self.logger.info(f"Using environment config: {path}")
                    return path
                resolved = path.resolve()
                if resolved.exists():
                    self.logger.info(f"Using environment config: {resolved}")
                    return resolved
            except Exception as e:
                self.logger.warning(f"Error resolving environment path: {e}")

        # Finally, use default config
        self.logger.info(f"Using default config: {self.DEFAULT_CONFIG_PATH}")
        return self.DEFAULT_CONFIG_PATH

    def _load_config(self) -> NovaConfig:
        """Load configuration from file.

        Returns:
            Loaded configuration.

        Raises:
            ValueError: If configuration is invalid.
        """
        try:
            self.logger.debug(f"Loading configuration from: {self.config_path}")
            
            # Only load default config if we're using a custom config
            if self.config_path.resolve() != self.DEFAULT_CONFIG_PATH.resolve():
                self.logger.debug("Loading and merging configurations")
                self.logger.debug(f"Reading default config: {self.DEFAULT_CONFIG_PATH}")
                with open(self.DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
                    default_config = yaml.safe_load(f) or {}

                self.logger.debug(f"Reading user config: {self.config_path}")
                with open(self.config_path, "r", encoding="utf-8") as f:
                    user_config = yaml.safe_load(f) or {}

                # Deep merge configs
                config_dict = self._deep_merge(default_config, user_config)
                self.logger.debug("Configurations merged successfully")
            else:
                # Just load the default config
                self.logger.debug("Loading default configuration only")
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config_dict = yaml.safe_load(f) or {}

            # Log only non-sensitive parts
            if "base_dir" in config_dict:
                self.logger.info(f"Base directory: {config_dict['base_dir']}")
            if "input_dir" in config_dict:
                self.logger.info(f"Input directory: {config_dict['input_dir']}")

            # Validate required fields before creating NovaConfig
            required_fields = [
                "base_dir",
                "input_dir",
                "output_dir",
                "processing_dir",
                "cache",
            ]
            missing_fields = [
                field for field in required_fields if field not in config_dict
            ]
            if missing_fields:
                raise ValueError(
                    f"Missing required configuration fields: {', '.join(missing_fields)}"
                )

            # Ensure cache has required fields
            if "cache" in config_dict:
                if not isinstance(config_dict["cache"], dict):
                    raise ValueError("Cache configuration must be a dictionary")
                if "dir" not in config_dict["cache"]:
                    raise ValueError("Cache configuration missing required field: dir")

            # Expand environment variables in paths
            def expand_path(path: str) -> str:
                """Expand environment variables and user home in path."""
                # First replace ${VAR} style variables
                import re

                pattern = r"\${([^}]+)}"
                matches = re.finditer(pattern, path)
                for match in matches:
                    var_name = match.group(1)
                    # If var_name is base_dir, use the config's base_dir
                    if var_name == "base_dir" and "base_dir" in config_dict:
                        var_value = config_dict["base_dir"]
                    else:
                        var_value = os.environ.get(var_name)
                    if var_value:
                        path = path.replace(f"${{{var_name}}}", str(var_value))
                # Then expand user home
                return os.path.expanduser(path)

            # Expand base_dir first since other paths may reference it
            base_dir = expand_path(config_dict["base_dir"])
            config_dict["base_dir"] = base_dir

            # Expand other paths, replacing ${base_dir} with actual base_dir
            for key in ["input_dir", "output_dir", "processing_dir"]:
                if key in config_dict:
                    path = config_dict[key]
                    if isinstance(path, str):  # Only process if it's a string
                        config_dict[key] = expand_path(path)

            # Handle cache directory
            if "cache" in config_dict and "dir" in config_dict["cache"]:
                cache_dir = config_dict["cache"]["dir"]
                if isinstance(cache_dir, str):  # Only process if it's a string
                    config_dict["cache"]["dir"] = expand_path(cache_dir)

            # Handle logging directory
            if "logging" in config_dict and "log_dir" in config_dict["logging"]:
                log_dir = config_dict["logging"]["log_dir"]
                if isinstance(log_dir, str):  # Only process if it's a string
                    config_dict["logging"]["log_dir"] = expand_path(log_dir)

            return NovaConfig(**config_dict)

        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise

    def _deep_merge(self, default: dict, override: dict) -> dict:
        """Deep merge two dictionaries.
        
        Args:
            default: Default dictionary
            override: Dictionary to override defaults
            
        Returns:
            Merged dictionary
        """
        result = default.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
                
        return result

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

    @pipeline.setter
    def pipeline(self, value: PipelineConfig) -> None:
        """Set pipeline configuration.

        Args:
            value: Pipeline configuration to set.
        """
        self.config.pipeline = value

    @property
    def apis(self) -> APIConfig:
        """Get API configuration."""
        return self.config.apis

    def __str__(self) -> str:
        """Get string representation of config manager."""
        return str(self.config)

    def __fspath__(self) -> str:
        """Return the file system path representation.

        This makes ConfigManager compatible with os.PathLike.
        """
        return str(self.input_dir)
