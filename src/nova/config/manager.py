"""Configuration manager for Nova."""
import logging
import os
from pathlib import Path
from typing import Optional, Union

import yaml

from nova.config.settings import APIConfig, CacheConfig, NovaConfig, PipelineConfig

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

        if isinstance(config, NovaConfig):
            self.config = config
            self.config_path = None
            self.logger.info(f"Using provided NovaConfig instance")
        else:
            self.config_path = self._resolve_config_path(config)
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
            ValueError: If configuration is invalid.
        """
        try:
            # Load default config first
            with open(self.DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
                default_config = yaml.safe_load(f) or {}

            # Load user config
            with open(self.config_path, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f) or {}

            self.logger.debug(f"User config APIs: {user_config.get('apis', {})}")

            # Merge configs (user config overrides default)
            config_dict = {**default_config, **user_config}

            self.logger.debug(f"Merged config APIs: {config_dict.get('apis', {})}")

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
                    var_value = os.environ.get(var_name)
                    if var_value:
                        path = path.replace(f"${{{var_name}}}", var_value)
                # Then expand user home
                return os.path.expanduser(path)

            # Expand base_dir first since other paths may reference it
            base_dir = expand_path(config_dict["base_dir"])
            config_dict["base_dir"] = base_dir

            # Expand other paths, replacing ${base_dir} with actual base_dir
            for key in ["input_dir", "output_dir", "processing_dir"]:
                if key in config_dict:
                    path = config_dict[key].replace("${base_dir}", base_dir)
                    config_dict[key] = expand_path(path)

            # Handle cache directory
            if "cache" in config_dict and "dir" in config_dict["cache"]:
                cache_dir = config_dict["cache"]["dir"].replace("${base_dir}", base_dir)
                config_dict["cache"]["dir"] = expand_path(cache_dir)

            # Handle logging directory
            if "logging" in config_dict and "log_dir" in config_dict["logging"]:
                log_dir = config_dict["logging"]["log_dir"].replace(
                    "${base_dir}", base_dir
                )
                config_dict["logging"]["log_dir"] = expand_path(log_dir)

            # Handle API configuration
            if "apis" in config_dict:
                self.logger.debug("Found APIs configuration")
                apis_config = config_dict["apis"]
                if apis_config and "openai" in apis_config:
                    self.logger.debug("Found OpenAI configuration")
                    openai_config = apis_config["openai"]
                    if openai_config and "api_key" in openai_config:
                        self.logger.debug("Found OpenAI API key")
                        api_key = str(
                            openai_config["api_key"]
                        ).strip()  # Convert to string and strip whitespace
                        if api_key:
                            openai_config["api_key"] = api_key
                            if api_key:
                                self.logger.debug(
                                    f"OpenAI API key loaded: {api_key[:8]}..."
                                )
                                self.logger.debug(
                                    f"OpenAI API key type: {type(api_key)}"
                                )
                                self.logger.debug(
                                    f"OpenAI API key length: {len(api_key)}"
                                )
                            else:
                                self.logger.debug("OpenAI API key is None")
                        else:
                            self.logger.debug("OpenAI API key is empty")
                            openai_config["api_key"] = None
                    else:
                        self.logger.debug("No OpenAI API key found in config")
                else:
                    self.logger.debug("No OpenAI configuration found")
            else:
                self.logger.debug("No APIs configuration found")

            # Create NovaConfig instance which will validate all fields
            try:
                return NovaConfig(**config_dict)
            except Exception as e:
                raise ValueError(f"Invalid configuration: {str(e)}")

        except Exception as e:
            raise ValueError(f"Failed to load configuration: {str(e)}")

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
