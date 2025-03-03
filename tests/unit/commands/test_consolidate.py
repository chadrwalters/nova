"""
Unit tests for the consolidate command.

This module tests the consolidate-markdown command handler.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nova.commands.consolidate import consolidate_markdown_command
from nova.config.models import (
    ConsolidateMarkdownConfig,
    ConsolidateMarkdownOutputConfig,
    ConsolidateMarkdownSourceConfig,
)
from nova.exceptions import ConfigurationError, ConsolidationError


class TestConsolidateMarkdownCommand:
    """Tests for the consolidate_markdown_command function."""

    @patch("nova.commands.consolidate.load_config")
    @patch("consolidate_markdown.runner.Runner")
    async def test_consolidate_markdown_command_success(
        self, mock_runner_class, mock_load_config, tmp_path
    ):
        """Test the consolidate_markdown_command function with a successful execution."""
        # Create a temporary configuration file
        config_file = tmp_path / "config.toml"
        config_file.touch()

        # Create a mock configuration with the nested structure
        mock_source = MagicMock(spec=ConsolidateMarkdownSourceConfig)
        mock_source.directory = str(tmp_path / "source")
        mock_source.include_patterns = ["**/*.md"]
        mock_source.exclude_patterns = []

        mock_output = MagicMock(spec=ConsolidateMarkdownOutputConfig)
        mock_output.directory = str(tmp_path / "output")

        mock_config = MagicMock(spec=ConsolidateMarkdownConfig)
        mock_config.source = mock_source
        mock_config.output = mock_output

        mock_load_config.return_value = mock_config

        # Mock the Runner class
        mock_runner_instance = mock_runner_class.return_value
        mock_runner_instance.run = AsyncMock()

        # Call the function
        await consolidate_markdown_command(str(config_file))

        # Verify load_config was called with the correct arguments
        mock_load_config.assert_called_once_with(
            str(config_file.resolve()), ConsolidateMarkdownConfig
        )

        # Verify Runner was initialized with the correct configuration
        mock_runner_class.assert_called_once()
        config_arg = mock_runner_class.call_args[1]["config"]
        assert config_arg["source"]["directory"] == str(tmp_path / "source")
        assert config_arg["source"]["include_patterns"] == ["**/*.md"]
        assert config_arg["source"]["exclude_patterns"] == []
        assert config_arg["output"]["directory"] == str(tmp_path / "output")

        # Verify run was called
        mock_runner_instance.run.assert_called_once()

    @patch("nova.commands.consolidate.load_config")
    async def test_configuration_file_not_found(self, mock_load_config):
        """Test handling of a nonexistent configuration file."""
        # Mock the load_config function to raise FileNotFoundError
        mock_load_config.side_effect = FileNotFoundError("File not found")

        # Call the command and expect a ConfigurationError
        with pytest.raises(ConfigurationError) as excinfo:
            await consolidate_markdown_command("nonexistent.toml")

        # Verify the error message
        assert "Configuration file not found" in str(excinfo.value)
        assert excinfo.value.config_file == str(Path("nonexistent.toml").resolve())

    @patch("nova.commands.consolidate.load_config")
    async def test_invalid_configuration(self, mock_load_config):
        """Test handling of an invalid configuration."""
        # Mock the load_config function to raise ValueError
        mock_load_config.side_effect = ValueError("Invalid configuration")

        # Call the command and expect a ConfigurationError
        with pytest.raises(ConfigurationError) as excinfo:
            await consolidate_markdown_command("invalid.toml")

        # Verify the error message
        assert "Invalid configuration" in str(excinfo.value)
        assert excinfo.value.config_file == str(Path("invalid.toml").resolve())

    @patch("nova.commands.consolidate.load_config")
    @patch(
        "consolidate_markdown.runner.Runner",
        side_effect=ImportError("Runner not found"),
    )
    async def test_consolidate_markdown_import_error(
        self, mock_runner_class, mock_load_config, tmp_path
    ):
        """Test the consolidate_markdown_command function with an import error."""
        # Create a temporary configuration file
        config_file = tmp_path / "config.toml"
        config_file.touch()

        # Create a mock configuration with the nested structure
        mock_source = MagicMock(spec=ConsolidateMarkdownSourceConfig)
        mock_source.directory = str(tmp_path / "source")
        mock_source.include_patterns = ["**/*.md"]
        mock_source.exclude_patterns = []

        mock_output = MagicMock(spec=ConsolidateMarkdownOutputConfig)
        mock_output.directory = str(tmp_path / "output")

        mock_config = MagicMock(spec=ConsolidateMarkdownConfig)
        mock_config.source = mock_source
        mock_config.output = mock_output

        mock_load_config.return_value = mock_config

        # Call the function and expect a ConsolidationError
        with pytest.raises(ConsolidationError) as excinfo:
            await consolidate_markdown_command(str(config_file))

        # Verify the error message
        assert "ConsolidateMarkdown library not found" in str(excinfo.value)

    @patch("nova.commands.consolidate.load_config")
    @patch("consolidate_markdown.runner.Runner")
    async def test_consolidate_markdown_error(
        self, mock_runner_class, mock_load_config, tmp_path
    ):
        """Test the consolidate_markdown_command function with a consolidation error."""
        # Create a temporary configuration file
        config_file = tmp_path / "config.toml"
        config_file.touch()

        # Create a mock configuration with the nested structure
        mock_source = MagicMock(spec=ConsolidateMarkdownSourceConfig)
        mock_source.directory = str(tmp_path / "source")
        mock_source.include_patterns = ["**/*.md"]
        mock_source.exclude_patterns = []

        mock_output = MagicMock(spec=ConsolidateMarkdownOutputConfig)
        mock_output.directory = str(tmp_path / "output")

        mock_config = MagicMock(spec=ConsolidateMarkdownConfig)
        mock_config.source = mock_source
        mock_config.output = mock_output

        mock_load_config.return_value = mock_config

        # Mock the Runner class to raise an exception during consolidation
        mock_runner_instance = mock_runner_class.return_value
        mock_runner_instance.run = AsyncMock(
            side_effect=Exception("Consolidation error")
        )

        # Call the function and expect a ConsolidationError
        with pytest.raises(ConsolidationError) as excinfo:
            await consolidate_markdown_command(str(config_file))

        # Verify the error message
        assert "Error during Markdown consolidation" in str(excinfo.value)
        assert "Consolidation error" in str(excinfo.value)
