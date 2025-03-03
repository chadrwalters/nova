"""
Integration tests for the configuration loading.

This module tests the end-to-end functionality of loading and validating configurations.
"""

import pytest
import toml

from nova.config.loader import load_config
from nova.config.models import ConsolidateMarkdownConfig, UploadMarkdownConfig
from nova.exceptions import ConfigurationError


@pytest.fixture
def temp_consolidate_config_file(tmp_path):
    """Create a temporary consolidate-markdown configuration file."""
    config_file = tmp_path / "consolidate-markdown.toml"

    # Create source and output directories
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    config = {
        "source": {
            "directory": str(source_dir),
            "include_patterns": ["**/*.md"],
            "exclude_patterns": ["**/excluded/**"],
        },
        "output": {
            "directory": str(output_dir),
        },
        "logging": {
            "level": "INFO",
        },
    }

    with open(config_file, "w") as f:
        toml.dump(config, f)

    return config_file


@pytest.fixture
def temp_upload_config_file(tmp_path):
    """Create a temporary upload-markdown configuration file."""
    config_file = tmp_path / "upload-markdown.toml"

    config = {
        "graphlit": {
            "organization_id": "test-org-id",
            "environment_id": "test-env-id",
            "jwt_secret": "test-jwt-secret",
        },
        "logging": {
            "level": "INFO",
        },
    }

    with open(config_file, "w") as f:
        toml.dump(config, f)

    return config_file


class TestConfigIntegration:
    """Integration tests for the configuration loading."""

    def test_load_consolidate_config(self, temp_consolidate_config_file, tmp_path):
        """Test loading a consolidate-markdown configuration file."""
        # Load the configuration
        config = load_config(
            str(temp_consolidate_config_file), ConsolidateMarkdownConfig
        )

        # Verify the configuration was loaded correctly
        assert isinstance(config, ConsolidateMarkdownConfig)
        assert config.source.directory == str(tmp_path / "source")
        assert config.output.directory == str(tmp_path / "output")
        assert config.source.include_patterns == ["**/*.md"]
        assert config.source.exclude_patterns == ["**/excluded/**"]
        assert config.logging.level == "INFO"

    def test_load_upload_config(self, temp_upload_config_file):
        """Test loading an upload-markdown configuration file."""
        # Load the configuration
        config = load_config(str(temp_upload_config_file), UploadMarkdownConfig)

        # Verify the configuration was loaded correctly
        assert isinstance(config, UploadMarkdownConfig)
        assert config.graphlit.organization_id == "test-org-id"
        assert config.graphlit.environment_id == "test-env-id"
        assert config.graphlit.jwt_secret == "test-jwt-secret"
        assert config.logging.level == "INFO"

    def test_nonexistent_config_file(self):
        """Test handling of a nonexistent configuration file."""
        # Attempt to load a nonexistent configuration file
        with pytest.raises(ConfigurationError) as excinfo:
            load_config("nonexistent.toml", ConsolidateMarkdownConfig)

        # Verify the error message
        assert "Configuration file not found" in str(excinfo.value)

    def test_invalid_config_file(self, tmp_path):
        """Test handling of an invalid configuration file."""
        # Create an invalid configuration file
        config_file = tmp_path / "invalid.toml"
        config_file.write_text("This is not a valid TOML file")

        # Attempt to load the invalid configuration file
        with pytest.raises(ConfigurationError) as excinfo:
            load_config(str(config_file), ConsolidateMarkdownConfig)

        # Verify the error message
        assert "Invalid configuration" in str(excinfo.value)

    def test_missing_required_fields(self, tmp_path):
        """Test handling of a configuration file with missing required fields."""
        # Create a configuration file with missing required fields
        config_file = tmp_path / "missing-fields.toml"

        # Create source directory
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        config = {
            "source": {
                "directory": str(source_dir),
                # Missing include_patterns and exclude_patterns (should use defaults)
            },
            # Missing output section
            "logging": {
                "level": "INFO",
            },
        }

        with open(config_file, "w") as f:
            toml.dump(config, f)

        # Attempt to load the configuration file
        with pytest.raises(ConfigurationError) as excinfo:
            load_config(str(config_file), ConsolidateMarkdownConfig)

        # Verify the error message
        assert "output" in str(excinfo.value)

    def test_invalid_field_values(self, tmp_path):
        """Test handling of a configuration file with invalid field values."""
        # Create a configuration file with invalid field values
        config_file = tmp_path / "invalid-values.toml"

        # Create source directory
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        config = {
            "source": {
                "directory": str(source_dir),
                "include_patterns": "not-a-list",  # Should be a list
                "exclude_patterns": [],
            },
            "output": {
                "directory": str(output_dir),
            },
            "logging": {
                "level": "INVALID_LEVEL",  # Invalid log level
            },
        }

        with open(config_file, "w") as f:
            toml.dump(config, f)

        # Attempt to load the configuration file
        with pytest.raises(ConfigurationError) as excinfo:
            load_config(str(config_file), ConsolidateMarkdownConfig)

        # Verify the error message
        assert "include_patterns" in str(excinfo.value)

    def test_nonexistent_directories(self, tmp_path):
        """Test handling of a configuration file with nonexistent directories."""
        # Create a configuration file with nonexistent directories
        config_file = tmp_path / "nonexistent-dirs.toml"

        config = {
            "source": {
                "directory": str(tmp_path / "nonexistent-source"),
                "include_patterns": ["**/*.md"],
                "exclude_patterns": [],
            },
            "output": {
                "directory": str(tmp_path / "nonexistent-output"),
            },
            "logging": {
                "level": "INFO",
            },
        }

        with open(config_file, "w") as f:
            toml.dump(config, f)

        # Attempt to load the configuration file
        with pytest.raises(ConfigurationError) as excinfo:
            load_config(str(config_file), ConsolidateMarkdownConfig)

        # Verify the error message
        assert "Directory does not exist" in str(excinfo.value)
