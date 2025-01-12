"""Tests for Nova configuration system."""

import os
from pathlib import Path

import pytest
import yaml

from nova.config import NovaConfig, load_config


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    """Create a temporary config file."""
    config_data = {
        "paths": {
            "input_dir": str(tmp_path / "input"),
            "processing_dir": str(tmp_path / ".nova/processing"),
            "vector_store_dir": str(tmp_path / ".nova/vectorstore"),
            "logs_dir": str(tmp_path / ".nova/logs"),
            "state_dir": str(tmp_path / ".nova/state"),
        },
        "api": {"anthropic_key": "test-key"},
    }

    config_path = tmp_path / "nova.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)

    return config_path


def test_config_validation(config_file: Path) -> None:
    """Test configuration validation."""
    config = load_config(str(config_file))

    assert isinstance(config, NovaConfig)
    assert config.paths.input_dir.is_absolute()
    assert config.api.anthropic_key == "test-key"


def test_config_env_override(config_file: Path) -> None:
    """Test environment variable override."""
    os.environ["NOVA_API_ANTHROPIC_KEY"] = "env-key"

    config = load_config(str(config_file))
    assert config.api.anthropic_key == "env-key"

    del os.environ["NOVA_API_ANTHROPIC_KEY"]


def test_config_directory_creation(tmp_path: Path) -> None:
    """Test automatic directory creation."""
    config = NovaConfig(
        paths=NovaConfig.Paths(
            processing_dir=tmp_path / ".nova/processing",
            vector_store_dir=tmp_path / ".nova/vectorstore",
            logs_dir=tmp_path / ".nova/logs",
            state_dir=tmp_path / ".nova/state",
        )
    )

    assert config.paths.processing_dir.exists()
    assert config.paths.vector_store_dir.exists()
    assert config.paths.logs_dir.exists()
    assert config.paths.state_dir.exists()
