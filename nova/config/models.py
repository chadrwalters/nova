"""
Configuration models for the Nova CLI tool.

This module defines Pydantic models for configuration validation.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from pydantic import BaseModel, Field, field_validator


class GraphlitConfig(BaseModel):
    """Pydantic model for Graphlit configuration."""

    organization_id: str
    environment_id: str
    jwt_secret: str

    @field_validator("organization_id", "environment_id", "jwt_secret")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate that the value is not empty."""
        if not v or not v.strip():
            raise ValueError("Value cannot be empty")
        return v


class LoggingConfig(BaseModel):
    """Pydantic model for logging configuration."""

    level: str = Field(default="INFO")

    @field_validator("level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate that the log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()


class UploadConfig(BaseModel):
    """Pydantic model for upload configuration in the unified config file."""

    output_dir: str = Field(default="output")

    @field_validator("output_dir")
    @classmethod
    def validate_output_dir(cls, v: str) -> str:
        """Validate that the output directory exists."""
        path = Path(v).resolve()
        if not path.exists():
            raise ValueError(f"Output directory does not exist: {path}")
        if not path.is_dir():
            raise ValueError(f"Not a directory: {path}")
        return str(path)


class ConsolidateSourceConfig(BaseModel):
    """Pydantic model for a consolidate source in the unified config file."""

    type: str
    srcDir: str
    destDir: str


class ConsolidateGlobalConfig(BaseModel):
    """Pydantic model for consolidate global configuration in the unified config file."""

    cm_dir: Optional[str] = None
    force_generation: Optional[bool] = None
    no_image: Optional[bool] = None
    api_provider: Optional[str] = None
    openai_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openrouter_key: Optional[str] = None
    openrouter_base_url: Optional[str] = None


class ConsolidateModelsConfig(BaseModel):
    """Pydantic model for consolidate models configuration in the unified config file."""

    default_model: Optional[str] = None


class ConsolidateConfig(BaseModel):
    """Pydantic model for consolidate configuration in the unified config file."""

    global_: Optional[ConsolidateGlobalConfig] = Field(default=None, alias="global")
    models: Optional[ConsolidateModelsConfig] = None
    sources: Optional[List[ConsolidateSourceConfig]] = None


class MainConfig(BaseModel):
    """Pydantic model for the main configuration file."""

    graphlit: GraphlitConfig
    upload: Optional[UploadConfig] = None
    consolidate: Optional[ConsolidateConfig] = None
    logging: Optional[LoggingConfig] = Field(default_factory=LoggingConfig)


class UploadMarkdownConfig(BaseModel):
    """Pydantic model for upload-markdown configuration."""

    graphlit: GraphlitConfig
    output_dir: str = Field(default="output")
    logging: Optional[LoggingConfig] = Field(default_factory=LoggingConfig)

    @field_validator("output_dir")
    @classmethod
    def validate_output_dir(cls, v: str) -> str:
        """Validate that the output directory exists."""
        path = Path(v).resolve()
        if not path.exists():
            raise ValueError(f"Output directory does not exist: {path}")
        if not path.is_dir():
            raise ValueError(f"Not a directory: {path}")
        return str(path)


class ConsolidateMarkdownSourceConfig(BaseModel):
    """Pydantic model for consolidate-markdown source configuration."""

    directory: str
    include_patterns: List[str] = Field(default_factory=lambda: ["**/*.md"])
    exclude_patterns: List[str] = Field(default_factory=list)

    @field_validator("directory")
    @classmethod
    def validate_directory(cls, v: str) -> str:
        """Validate that the directory exists and is a directory."""
        path = Path(v).resolve()
        if not path.exists():
            raise ValueError(f"Directory does not exist: {path}")
        if not path.is_dir():
            raise ValueError(f"Not a directory: {path}")
        return str(path)


class ConsolidateMarkdownOutputConfig(BaseModel):
    """Pydantic model for consolidate-markdown output configuration."""

    directory: str

    @field_validator("directory")
    @classmethod
    def validate_directory(cls, v: str) -> str:
        """Validate that the directory exists and is a directory."""
        path = Path(v).resolve()
        if not path.exists():
            # Create the directory if it doesn't exist
            path.mkdir(parents=True, exist_ok=True)
        elif not path.is_dir():
            raise ValueError(f"Not a directory: {path}")
        return str(path)


class ConsolidateMarkdownConfig(BaseModel):
    """Pydantic model for the consolidate-markdown configuration file."""

    source: ConsolidateMarkdownSourceConfig
    output: ConsolidateMarkdownOutputConfig
    logging: Optional[LoggingConfig] = Field(default_factory=LoggingConfig)


def load_config(config_path: str, config_model: type) -> BaseModel:
    """
    Load and validate configuration from a TOML file using a Pydantic model.

    Args:
        config_path: Path to the configuration file.
        config_model: Pydantic model class to use for validation.

    Returns:
        Validated configuration object.

    Raises:
        FileNotFoundError: If the configuration file doesn't exist.
        ValueError: If the configuration is invalid.
    """
    import logging

    config_file = Path(config_path).resolve()
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_file, "rb") as f:
            # Use tomllib if available (Python 3.11+), otherwise fall back to toml
            try:
                import tomllib

                config_dict = tomllib.load(f)
            except ImportError:
                import toml

                config_dict = toml.load(f)

        # Validate configuration using Pydantic model
        return config_model(**config_dict)
    except Exception as e:
        logging.error(f"Error parsing configuration file: {e}")
        raise ValueError(f"Invalid configuration: {e}")
