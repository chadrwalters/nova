"""
Integration tests for the Nova CLI entry point.

This module tests the end-to-end functionality of the CLI entry point.
"""

from unittest.mock import AsyncMock, patch

import pytest
import toml

from nova.cli import main


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary directory with configuration files."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create source and output directories
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Create a consolidate-markdown config file
    consolidate_config = {
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

    with open(config_dir / "consolidate-markdown.toml", "w") as f:
        toml.dump(consolidate_config, f)

    # Create an upload-markdown config file
    upload_config = {
        "graphlit": {
            "organization_id": "test-org-id",
            "environment_id": "test-env-id",
            "jwt_secret": "test-jwt-secret",
        },
        "logging": {
            "level": "INFO",
        },
    }

    with open(config_dir / "upload-markdown.toml", "w") as f:
        toml.dump(upload_config, f)

    return config_dir


class TestCLIIntegration:
    """Integration tests for the Nova CLI entry point."""

    def test_version_flag(self):
        """Test the --version flag."""
        with pytest.raises(SystemExit) as excinfo:
            main(["--version"])

        assert excinfo.value.code == 0

    @patch("nova.cli.consolidate_markdown_command", new_callable=AsyncMock)
    def test_consolidate_markdown_command(self, mock_consolidate, temp_config_dir):
        """Test the consolidate-markdown command."""
        # Set up the mock to return None (success)
        mock_consolidate.return_value = None

        # Run the command
        result = main(
            [
                "consolidate-markdown",
                "--config",
                str(temp_config_dir / "consolidate-markdown.toml"),
            ]
        )

        # Verify the command was successful
        assert result == 0

        # Verify the consolidate_markdown_command was called with the correct arguments
        mock_consolidate.assert_called_once_with(
            str(temp_config_dir / "consolidate-markdown.toml")
        )

    @patch("nova.cli.upload_markdown_command", new_callable=AsyncMock)
    def test_upload_markdown_command(self, mock_upload, temp_config_dir, tmp_path):
        """Test the upload-markdown command."""
        # Set up the mock to return None (success)
        mock_upload.return_value = None

        # Create an output directory
        output_dir = tmp_path / "output"
        output_dir.mkdir(exist_ok=True)

        # Run the command
        result = main(
            [
                "upload-markdown",
                "--config",
                str(temp_config_dir / "upload-markdown.toml"),
                "--output-dir",
                str(output_dir),
            ]
        )

        # Verify the command was successful
        assert result == 0

        # Verify the upload_markdown_command was called with the correct arguments
        mock_upload.assert_called_once_with(
            str(temp_config_dir / "upload-markdown.toml"), str(output_dir), False
        )

    @patch("nova.cli.upload_markdown_command", new_callable=AsyncMock)
    def test_upload_markdown_command_with_dry_run(
        self, mock_upload, temp_config_dir, tmp_path
    ):
        """Test the upload-markdown command with the dry-run flag."""
        # Set up the mock to return None (success)
        mock_upload.return_value = None

        # Create an output directory
        output_dir = tmp_path / "output"
        output_dir.mkdir(exist_ok=True)

        # Run the command
        result = main(
            [
                "upload-markdown",
                "--config",
                str(temp_config_dir / "upload-markdown.toml"),
                "--output-dir",
                str(output_dir),
                "--dry-run",
            ]
        )

        # Verify the command was successful
        assert result == 0

        # Verify the upload_markdown_command was called with the correct arguments
        mock_upload.assert_called_once_with(
            str(temp_config_dir / "upload-markdown.toml"), str(output_dir), True
        )

    def test_no_command(self):
        """Test the behavior when no command is provided."""
        # Run the CLI without a command
        with pytest.raises(SystemExit) as excinfo:
            main([])

        # Verify the command exited with the correct exit code
        assert excinfo.value.code == 0

    @patch("nova.cli.consolidate_markdown_command", new_callable=AsyncMock)
    def test_unexpected_error(self, mock_consolidate, temp_config_dir):
        """Test handling of an unexpected error."""
        # Set up the mock to raise an exception
        mock_consolidate.side_effect = Exception("Unexpected error")

        # Run the command
        result = main(
            [
                "consolidate-markdown",
                "--config",
                str(temp_config_dir / "consolidate-markdown.toml"),
            ]
        )

        # Verify the command failed with the correct exit code
        assert result == 1

    @patch("nova.cli.consolidate_markdown_command", new_callable=AsyncMock)
    def test_keyboard_interrupt(self, mock_consolidate, temp_config_dir):
        """Test handling of a keyboard interrupt."""
        # Set up the mock to raise a KeyboardInterrupt
        mock_consolidate.side_effect = KeyboardInterrupt()

        # Run the command
        result = main(
            [
                "consolidate-markdown",
                "--config",
                str(temp_config_dir / "consolidate-markdown.toml"),
            ]
        )

        # Verify the command failed with the correct exit code
        assert result == 130

    @patch("nova.cli.consolidate_markdown_command", new_callable=AsyncMock)
    def test_help_flag(self, mock_consolidate):
        """Test the --help flag."""
        with pytest.raises(SystemExit) as excinfo:
            main(["--help"])

        assert excinfo.value.code == 0

        # Verify the consolidate_markdown_command was not called
        mock_consolidate.assert_not_called()

    @patch("nova.cli.consolidate_markdown_command", new_callable=AsyncMock)
    def test_command_help_flag(self, mock_consolidate):
        """Test the command --help flag."""
        with pytest.raises(SystemExit) as excinfo:
            main(["consolidate-markdown", "--help"])

        assert excinfo.value.code == 0

        # Verify the consolidate_markdown_command was not called
        mock_consolidate.assert_not_called()
