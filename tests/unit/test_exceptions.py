"""
Unit tests for the exceptions module.

This module tests the custom exception classes.
"""

from nova.exceptions import (
    ConfigurationError,
    ConsolidationError,
    GraphlitClientError,
    NovaError,
    UploadError,
)


class TestNovaError:
    """Tests for the NovaError class."""

    def test_init(self):
        """Test initialization with a message."""
        error = NovaError("Test error")
        assert error.message == "Test error"
        assert error.exit_code == 1
        assert str(error) == "Test error"

    def test_init_with_exit_code(self):
        """Test initialization with a custom exit code."""
        error = NovaError("Test error", exit_code=42)
        assert error.message == "Test error"
        assert error.exit_code == 42


class TestConfigurationError:
    """Tests for the ConfigurationError class."""

    def test_init(self):
        """Test initialization with a message."""
        error = ConfigurationError("Configuration error")
        assert error.message == "Configuration error"
        assert error.exit_code == 2
        assert error.config_file is None
        assert str(error) == "Configuration error"

    def test_init_with_config_file(self):
        """Test initialization with a config file."""
        error = ConfigurationError("Configuration error", config_file="config.toml")
        assert error.message == "Configuration error (config file: config.toml)"
        assert error.exit_code == 2
        assert error.config_file == "config.toml"

    def test_init_with_exit_code(self):
        """Test initialization with a custom exit code."""
        error = ConfigurationError("Configuration error", exit_code=42)
        assert error.message == "Configuration error"
        assert error.exit_code == 42


class TestConsolidationError:
    """Tests for the ConsolidationError class."""

    def test_init(self):
        """Test initialization with a message."""
        error = ConsolidationError("Consolidation error")
        assert error.message == "Consolidation error"
        assert error.exit_code == 3
        assert error.file_path is None
        assert str(error) == "Consolidation error"

    def test_init_with_file_path(self):
        """Test initialization with a file path."""
        error = ConsolidationError("Consolidation error", file_path="file.md")
        assert error.message == "Consolidation error (file: file.md)"
        assert error.exit_code == 3
        assert error.file_path == "file.md"

    def test_init_with_exit_code(self):
        """Test initialization with a custom exit code."""
        error = ConsolidationError("Consolidation error", exit_code=42)
        assert error.message == "Consolidation error"
        assert error.exit_code == 42


class TestUploadError:
    """Tests for the UploadError class."""

    def test_init(self):
        """Test initialization with a message."""
        error = UploadError("Upload error")
        assert error.message == "Upload error"
        assert error.exit_code == 4
        assert error.file_path is None
        assert str(error) == "Upload error"

    def test_init_with_file_path(self):
        """Test initialization with a file path."""
        error = UploadError("Upload error", file_path="file.md")
        assert error.message == "Upload error (file: file.md)"
        assert error.exit_code == 4
        assert error.file_path == "file.md"

    def test_init_with_exit_code(self):
        """Test initialization with a custom exit code."""
        error = UploadError("Upload error", exit_code=42)
        assert error.message == "Upload error"
        assert error.exit_code == 42


class TestGraphlitClientError:
    """Tests for the GraphlitClientError class."""

    def test_init(self):
        """Test initialization with a message."""
        error = GraphlitClientError("Graphlit client error")
        assert error.message == "Graphlit client error"
        assert error.exit_code == 5
        assert error.response is None
        assert str(error) == "Graphlit client error"

    def test_init_with_response(self):
        """Test initialization with a response."""
        response = {"error": "Not found"}
        error = GraphlitClientError("Graphlit client error", response=response)
        assert (
            error.message == "Graphlit client error (response: {'error': 'Not found'})"
        )
        assert error.exit_code == 5
        assert error.response == response

    def test_init_with_exit_code(self):
        """Test initialization with a custom exit code."""
        error = GraphlitClientError("Graphlit client error", exit_code=42)
        assert error.message == "Graphlit client error"
        assert error.exit_code == 42
