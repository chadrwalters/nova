"""Nova configuration management."""

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class NovaConfig(BaseModel):
    """Nova configuration model with validation."""

    class Paths(BaseModel):
        """Path configuration."""

        input_dir: Path = Field(
            default=Path(
                "~/Library/Mobile Documents/com~apple~CloudDocs/_NovaInput"
            ).expanduser(),
            description="Directory containing Bear.app exports",
        )
        processing_dir: Path = Field(
            default=Path(".nova/processing"),
            description="Directory for temporary processing files",
        )
        vector_store_dir: Path = Field(
            default=Path(".nova/vectorstore"),
            description="Directory for vector store data",
        )
        logs_dir: Path = Field(
            default=Path(".nova/logs"), description="Directory for log files"
        )
        state_dir: Path = Field(
            default=Path(".nova/state"), description="Directory for system state"
        )

        @field_validator("*")
        @classmethod
        def expand_path(cls, v: Path) -> Path:
            """Expand user and make path absolute."""
            return v.expanduser().resolve()

        model_config = {"arbitrary_types_allowed": True}

    class API(BaseModel):
        """API configuration."""

        anthropic_key: str | None = Field(
            default=None, description="Anthropic API key for Claude access"
        )

    paths: Paths = Field(default_factory=Paths)
    api: API = Field(default_factory=API)

    @field_validator("paths")
    @classmethod
    def create_directories(cls, v: Paths) -> Paths:
        """Create necessary directories if they don't exist."""
        for path in [v.processing_dir, v.vector_store_dir, v.logs_dir, v.state_dir]:
            path.mkdir(parents=True, exist_ok=True)
        return v

    model_config = {"arbitrary_types_allowed": True}


def load_config(config_path: str | None = None) -> NovaConfig:
    """Load configuration from file and environment variables.

    Args:
        config_path: Path to config file. If None, uses default locations.

    Returns:
        Validated configuration object
    """
    # Default config locations
    config_locations = [
        "config/nova.yaml",
        "~/.config/nova/config.yaml",
        os.environ.get("NOVA_CONFIG", ""),
    ]

    # Add specified config path
    if config_path:
        config_locations.insert(0, config_path)

    # Load first existing config file
    config_data: dict[str, Any] = {}
    for loc in config_locations:
        if not loc:
            continue
        path = Path(loc).expanduser()
        if path.exists():
            with open(path) as f:
                config_data = yaml.safe_load(f) or {}
            break

    # Override with environment variables
    if "NOVA_API_ANTHROPIC_KEY" in os.environ:
        config_data.setdefault("api", {})["anthropic_key"] = os.environ[
            "NOVA_API_ANTHROPIC_KEY"
        ]

    if "NOVA_PATHS_INPUT_DIR" in os.environ:
        config_data.setdefault("paths", {})["input_dir"] = os.environ[
            "NOVA_PATHS_INPUT_DIR"
        ]

    return NovaConfig(**config_data)


# Global config instance
config = load_config()
