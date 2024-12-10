"""Configuration management functionality."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeAlias, TypedDict, Union, cast

import structlog
import yaml

from src.core.exceptions import ConfigError

logger = structlog.get_logger(__name__)

# Type aliases
PathMapping: TypeAlias = Dict[str, Path]
ConfigDict: TypeAlias = Dict[str, Any]
ValidationResult: TypeAlias = Union[None, str]


class ConfigData(TypedDict, total=False):
    """Type definition for configuration data."""

    input_dir: str
    output_dir: str
    temp_dir: str
    template_dir: str
    media_dir: str
    error_tolerance: bool
    log_level: str
    max_file_size: int
    allowed_extensions: List[str]
    excluded_patterns: List[str]
    metadata_fields: List[str]
    template_vars: Dict[str, str]


@dataclass
class ProcessingConfig:
    """Configuration for document processing."""
    
    # Base directories
    input_dir: Path      # Source markdown files
    output_dir: Path     # Final PDF output
    
    # Processing structure
    processing_dir: Path  # Root for all processing
    
    @property
    def html_dir(self) -> Path:
        """Directory for HTML files."""
        return self.processing_dir / "html"
        
    @property
    def temp_dir(self) -> Path:
        """Directory for temporary files."""
        return self.processing_dir / "temp"
        
    @property
    def media_dir(self) -> Path:
        """Directory for media files."""
        return self.processing_dir / "media"
        
    @property
    def attachments_dir(self) -> Path:
        """Directory for attachments."""
        return self.processing_dir / "attachments"
        
    @property
    def consolidated_dir(self) -> Path:
        """Directory for consolidated output."""
        return self.processing_dir / "consolidated"

    @classmethod
    def from_env(cls, env_config: dict) -> "ProcessingConfig":
        """Create config from environment variables."""
        return cls(
            input_dir=Path(env_config["NOVA_INPUT_DIR"]),
            output_dir=Path(env_config["NOVA_OUTPUT_DIR"]),
            processing_dir=Path(env_config["NOVA_PROCESSING_DIR"]),
        )


class ConfigManager:
    """Manager for configuration loading and validation."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """Initialize the configuration manager.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.logger = logger

    def load_config(self) -> ProcessingConfig:
        """Load configuration from file or use defaults.

        Returns:
            Loaded configuration

        Raises:
            ConfigError: If configuration loading or validation fails
        """
        try:
            if self.config_path and self.config_path.exists():
                return self._load_from_file()
            return self._get_default_config()

        except Exception as err:
            self.logger.error("Failed to load configuration", exc_info=err)
            raise ConfigError("Failed to load configuration") from err

    def _load_from_file(self) -> ProcessingConfig:
        """Load configuration from file.

        Returns:
            Loaded configuration

        Raises:
            ConfigError: If file loading or parsing fails
        """
        try:
            if not self.config_path:
                raise ConfigError("No configuration file path provided")

            # Load and validate YAML file
            yaml_data = yaml.safe_load(self.config_path.read_text())
            if not isinstance(yaml_data, dict):
                raise ConfigError("Invalid YAML format: expected dictionary")

            # Convert to typed dictionary
            config_data = cast(ConfigData, yaml_data)

            # Convert paths and create initial config
            path_config = {
                "input_dir": Path(config_data.get("input_dir", "input")),
                "output_dir": Path(config_data.get("output_dir", "output")),
                "temp_dir": Path(config_data.get("temp_dir", "temp")),
                "template_dir": Path(config_data.get("template_dir", "templates")),
                "media_dir": Path(config_data.get("media_dir", "media")),
            }

            # Create config object with all values
            config = ProcessingConfig(
                **path_config,
                error_tolerance=config_data.get("error_tolerance", False),
                log_level=config_data.get("log_level", "INFO"),
                max_file_size=config_data.get("max_file_size", 10 * 1024 * 1024),
                allowed_extensions=config_data.get(
                    "allowed_extensions", [".md", ".markdown"]
                ),
                excluded_patterns=config_data.get(
                    "excluded_patterns", [".*", "_*", "node_modules"]
                ),
                metadata_fields=config_data.get(
                    "metadata_fields", ["title", "author", "date", "tags"]
                ),
                template_vars=config_data.get("template_vars", {}),
            )

            # Validate configuration
            self._validate_config(config)

            return config

        except Exception as err:
            self.logger.error(
                "Failed to load configuration file",
                path=self.config_path,
                exc_info=err,
            )
            raise ConfigError(
                f"Failed to load configuration from {self.config_path}"
            ) from err

    def _get_default_config(self) -> ProcessingConfig:
        """Get default configuration.

        Returns:
            Default configuration

        Raises:
            ConfigError: If validation fails
        """
        config = ProcessingConfig(
            input_dir=Path("input"),
            output_dir=Path("output"),
            temp_dir=Path("temp"),
            template_dir=Path("templates"),
            media_dir=Path("media"),
        )

        # Validate configuration
        self._validate_config(config)

        return config

    def _validate_config(self, config: ProcessingConfig) -> None:
        """Validate configuration values.

        Args:
            config: Configuration to validate

        Raises:
            ConfigError: If validation fails
        """
        validation_errors: List[str] = []

        # Check directory paths
        for path_name, path in [
            ("input_dir", config.input_dir),
            ("output_dir", config.output_dir),
            ("temp_dir", config.temp_dir),
            ("template_dir", config.template_dir),
            ("media_dir", config.media_dir),
        ]:
            if not isinstance(path, Path):
                validation_errors.append(f"{path_name} must be a Path object")

        # Check numeric values
        if config.max_file_size <= 0:
            validation_errors.append("max_file_size must be positive")

        # Check list values
        if not config.allowed_extensions:
            validation_errors.append("allowed_extensions cannot be empty")

        # Check string values
        if config.log_level not in [
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
        ]:
            validation_errors.append("Invalid log_level")

        # Raise error if any validation failed
        if validation_errors:
            raise ConfigError("\n".join(validation_errors))


# Type hints for exports
__all__: list[str] = ["ConfigManager", "ProcessingConfig", "ConfigError"]
