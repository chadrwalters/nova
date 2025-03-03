"""
Unit tests for the configuration models.

This module tests the Pydantic models for configuration validation.
"""

import os
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from nova.config.models import (
    ConsolidateMarkdownConfig,
    ConsolidateMarkdownOutputConfig,
    ConsolidateMarkdownSourceConfig,
    GraphlitConfig,
    LoggingConfig,
    MainConfig,
    load_config,
)


class TestGraphlitConfig:
    """Tests for the GraphlitConfig model."""

    def test_valid_config(self):
        """Test that a valid configuration is accepted."""
        config = GraphlitConfig(
            organization_id="org123",
            environment_id="env456",
            jwt_secret="secret789",
        )
        assert config.organization_id == "org123"
        assert config.environment_id == "env456"
        assert config.jwt_secret == "secret789"

    def test_empty_values(self):
        """Test that empty values are rejected."""
        with pytest.raises(ValidationError):
            GraphlitConfig(
                organization_id="",
                environment_id="env456",
                jwt_secret="secret789",
            )

        with pytest.raises(ValidationError):
            GraphlitConfig(
                organization_id="org123",
                environment_id="",
                jwt_secret="secret789",
            )

        with pytest.raises(ValidationError):
            GraphlitConfig(
                organization_id="org123",
                environment_id="env456",
                jwt_secret="",
            )


class TestLoggingConfig:
    """Tests for the LoggingConfig model."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = LoggingConfig()
        assert config.level == "INFO"

    def test_valid_log_levels(self):
        """Test that valid log levels are accepted."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = LoggingConfig(level=level)
            assert config.level == level

        # Test case insensitivity
        config = LoggingConfig(level="debug")
        assert config.level == "DEBUG"

    def test_invalid_log_level(self):
        """Test that invalid log levels are rejected."""
        with pytest.raises(ValidationError):
            LoggingConfig(level="INVALID")


class TestMainConfig:
    """Tests for the MainConfig model."""

    def test_valid_config(self):
        """Test that a valid configuration is accepted."""
        config = MainConfig(
            graphlit=GraphlitConfig(
                organization_id="org123",
                environment_id="env456",
                jwt_secret="secret789",
            )
        )
        assert config.graphlit.organization_id == "org123"
        assert config.graphlit.environment_id == "env456"
        assert config.graphlit.jwt_secret == "secret789"
        assert config.logging.level == "INFO"  # Default value

    def test_custom_logging_config(self):
        """Test that a custom logging configuration is accepted."""
        config = MainConfig(
            graphlit=GraphlitConfig(
                organization_id="org123",
                environment_id="env456",
                jwt_secret="secret789",
            ),
            logging=LoggingConfig(level="DEBUG"),
        )
        assert config.logging.level == "DEBUG"


class TestConsolidateMarkdownSourceConfig:
    """Tests for the ConsolidateMarkdownSourceConfig model."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = ConsolidateMarkdownSourceConfig(directory=temp_dir)
            assert config.directory == str(Path(temp_dir).resolve())
            assert config.include_patterns == ["**/*.md"]
            assert config.exclude_patterns == []

    def test_custom_patterns(self):
        """Test that custom patterns are accepted."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = ConsolidateMarkdownSourceConfig(
                directory=temp_dir,
                include_patterns=["**/*.markdown", "**/*.md"],
                exclude_patterns=["**/README.md"],
            )
            assert config.include_patterns == ["**/*.markdown", "**/*.md"]
            assert config.exclude_patterns == ["**/README.md"]

    def test_nonexistent_directory(self):
        """Test that a nonexistent directory is rejected."""
        with pytest.raises(ValidationError):
            ConsolidateMarkdownSourceConfig(directory="/nonexistent/directory")

    def test_not_a_directory(self):
        """Test that a file is rejected."""
        with tempfile.NamedTemporaryFile() as temp_file:
            with pytest.raises(ValidationError):
                ConsolidateMarkdownSourceConfig(directory=temp_file.name)


class TestConsolidateMarkdownOutputConfig:
    """Tests for the ConsolidateMarkdownOutputConfig model."""

    def test_existing_directory(self):
        """Test that an existing directory is accepted."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = ConsolidateMarkdownOutputConfig(directory=temp_dir)
            assert config.directory == str(Path(temp_dir).resolve())

    def test_nonexistent_directory_creation(self):
        """Test that a nonexistent directory is created."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_dir = os.path.join(temp_dir, "nonexistent")
            config = ConsolidateMarkdownOutputConfig(directory=nonexistent_dir)
            assert config.directory == str(Path(nonexistent_dir).resolve())
            assert os.path.exists(nonexistent_dir)
            assert os.path.isdir(nonexistent_dir)

    def test_not_a_directory(self):
        """Test that a file is rejected."""
        with tempfile.NamedTemporaryFile() as temp_file:
            with pytest.raises(ValidationError):
                ConsolidateMarkdownOutputConfig(directory=temp_file.name)


class TestConsolidateMarkdownConfig:
    """Tests for the ConsolidateMarkdownConfig model."""

    def test_valid_config(self):
        """Test that a valid configuration is accepted."""
        with tempfile.TemporaryDirectory() as source_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                config = ConsolidateMarkdownConfig(
                    source=ConsolidateMarkdownSourceConfig(directory=source_dir),
                    output=ConsolidateMarkdownOutputConfig(directory=output_dir),
                )
                assert config.source.directory == str(Path(source_dir).resolve())
                assert config.output.directory == str(Path(output_dir).resolve())


class TestLoadConfig:
    """Tests for the load_config function."""

    def test_load_valid_config(self, tmp_path):
        """Test that a valid configuration file is loaded correctly."""
        config_file = tmp_path / "config.toml"
        with open(config_file, "w") as f:
            f.write(
                """
            [graphlit]
            organization_id = "org123"
            environment_id = "env456"
            jwt_secret = "secret789"

            [logging]
            level = "DEBUG"
            """
            )

        config = load_config(str(config_file), MainConfig)
        assert isinstance(config, MainConfig)
        assert config.graphlit.organization_id == "org123"
        assert config.graphlit.environment_id == "env456"
        assert config.graphlit.jwt_secret == "secret789"
        assert config.logging.level == "DEBUG"

    def test_load_nonexistent_config(self):
        """Test that a nonexistent configuration file raises an error."""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/config.toml", MainConfig)

    def test_load_invalid_config(self, tmp_path):
        """Test that an invalid configuration file raises an error."""
        config_file = tmp_path / "config.toml"
        with open(config_file, "w") as f:
            f.write(
                """
            [graphlit]
            # Missing required fields
            """
            )

        with pytest.raises(ValueError):
            load_config(str(config_file), MainConfig)
