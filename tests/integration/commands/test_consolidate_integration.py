"""
Integration tests for the consolidate-markdown command.

This module tests the end-to-end functionality of the consolidate-markdown command.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import toml

from nova.cli import main
from nova.exceptions import ConsolidationError


@pytest.fixture
def temp_source_dir(tmp_path):
    """Create a temporary source directory with Markdown files."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    # Create some Markdown files
    (source_dir / "file1.md").write_text("# File 1\n\nThis is file 1.")
    (source_dir / "file2.md").write_text("# File 2\n\nThis is file 2.")

    # Create a subdirectory with more Markdown files
    subdir = source_dir / "subdir"
    subdir.mkdir()
    (subdir / "file3.md").write_text("# File 3\n\nThis is file 3.")

    # Create a non-Markdown file
    (source_dir / "not-markdown.txt").write_text("This is not a Markdown file.")

    return source_dir


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def temp_config_file(tmp_path, temp_source_dir, temp_output_dir):
    """Create a temporary configuration file for the consolidate-markdown command."""
    config_file = tmp_path / "consolidate-markdown.toml"

    config = {
        "source": {
            "directory": str(temp_source_dir),
            "include_patterns": ["**/*.md"],
            "exclude_patterns": [],
        },
        "output": {
            "directory": str(temp_output_dir),
        },
    }

    with open(config_file, "w") as f:
        toml.dump(config, f)

    return config_file


class TestConsolidateMarkdownIntegration:
    """Integration tests for the consolidate-markdown command."""

    @patch("nova.commands.consolidate.load_config")
    @patch("consolidate_markdown.runner.Runner")
    async def test_successful_consolidation(
        self, mock_runner_class, mock_load_config, tmp_path
    ):
        """Test successful Markdown consolidation."""
        # Create a temporary configuration file
        config_file = tmp_path / "consolidate-markdown.toml"
        config_file.touch()

        # Create a mock configuration
        from nova.config.models import (
            ConsolidateMarkdownConfig,
            ConsolidateMarkdownOutputConfig,
            ConsolidateMarkdownSourceConfig,
        )

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

        # Call the command
        from nova.commands.consolidate import consolidate_markdown_command

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
    @patch("consolidate_markdown.runner.Runner")
    async def test_consolidation_with_custom_patterns(
        self, mock_runner_class, mock_load_config, tmp_path
    ):
        """Test Markdown consolidation with custom include and exclude patterns."""
        # Create a temporary configuration file
        config_file = tmp_path / "consolidate-markdown.toml"
        config_file.touch()

        # Create a mock configuration
        from nova.config.models import (
            ConsolidateMarkdownConfig,
            ConsolidateMarkdownOutputConfig,
            ConsolidateMarkdownSourceConfig,
        )

        mock_source = MagicMock(spec=ConsolidateMarkdownSourceConfig)
        mock_source.directory = str(tmp_path / "source")
        mock_source.include_patterns = ["**/*.md", "**/*.markdown"]
        mock_source.exclude_patterns = ["**/excluded/**"]

        mock_output = MagicMock(spec=ConsolidateMarkdownOutputConfig)
        mock_output.directory = str(tmp_path / "output")

        mock_config = MagicMock(spec=ConsolidateMarkdownConfig)
        mock_config.source = mock_source
        mock_config.output = mock_output

        mock_load_config.return_value = mock_config

        # Mock the Runner class
        mock_runner_instance = mock_runner_class.return_value
        mock_runner_instance.run = AsyncMock()

        # Call the command
        from nova.commands.consolidate import consolidate_markdown_command

        await consolidate_markdown_command(str(config_file))

        # Verify Runner was initialized with the correct configuration
        mock_runner_class.assert_called_once()
        config_arg = mock_runner_class.call_args[1]["config"]
        assert config_arg["source"]["include_patterns"] == ["**/*.md", "**/*.markdown"]
        assert config_arg["source"]["exclude_patterns"] == ["**/excluded/**"]
        assert config_arg["output"]["directory"] == str(tmp_path / "output")

        # Verify run was called
        mock_runner_instance.run.assert_called_once()

    def test_nonexistent_config_file(self):
        """Test handling of a nonexistent configuration file."""
        # Run the command with a nonexistent configuration file
        result = main(["consolidate-markdown", "--config", "nonexistent.toml"])

        # Verify the command failed with the correct exit code
        assert result == 2  # ConfigurationError exit code

    @patch("nova.commands.consolidate.load_config")
    @patch(
        "consolidate_markdown.runner.Runner",
        side_effect=ImportError("No module named 'consolidate_markdown'"),
    )
    async def test_consolidate_markdown_import_error(
        self, mock_runner_class, mock_load_config, tmp_path
    ):
        """Test handling of an import error for the consolidate_markdown library."""
        # Create a temporary configuration file
        config_file = tmp_path / "consolidate-markdown.toml"
        config_file.touch()

        # Create a mock configuration
        from nova.config.models import (
            ConsolidateMarkdownConfig,
            ConsolidateMarkdownOutputConfig,
            ConsolidateMarkdownSourceConfig,
        )

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

        # Call the command and expect a ConsolidationError
        from nova.commands.consolidate import consolidate_markdown_command

        with pytest.raises(ConsolidationError) as excinfo:
            await consolidate_markdown_command(str(config_file))

        # Verify the error message
        assert "ConsolidateMarkdown library not found" in str(excinfo.value)

    @patch("nova.commands.consolidate.load_config")
    @patch("consolidate_markdown.runner.Runner")
    async def test_consolidation_error(
        self, mock_runner_class, mock_load_config, tmp_path
    ):
        """Test handling of an error during consolidation."""
        # Create a temporary configuration file
        config_file = tmp_path / "consolidate-markdown.toml"
        config_file.touch()

        # Create a mock configuration
        from nova.config.models import (
            ConsolidateMarkdownConfig,
            ConsolidateMarkdownOutputConfig,
            ConsolidateMarkdownSourceConfig,
        )

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

        # Mock the Runner class to raise an exception
        mock_runner_instance = mock_runner_class.return_value
        mock_runner_instance.run = AsyncMock(
            side_effect=Exception("Consolidation error")
        )

        # Call the command and expect a ConsolidationError
        from nova.commands.consolidate import consolidate_markdown_command

        with pytest.raises(ConsolidationError) as excinfo:
            await consolidate_markdown_command(str(config_file))

        # Verify the error message
        assert "Error during Markdown consolidation" in str(excinfo.value)
