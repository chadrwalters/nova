"""
Unit tests for the CLI entry point.

This module tests the main CLI entry point for the Nova CLI tool.
"""

import argparse
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nova.cli import main, main_async, parse_args
from nova.exceptions import ConfigurationError, NovaError


class TestParseArgs:
    """Tests for the parse_args function."""

    def test_version(self):
        """Test the --version argument."""
        with pytest.raises(SystemExit) as excinfo:
            parse_args(["--version"])
        assert excinfo.value.code == 0

    def test_no_command(self):
        """Test parsing with no command."""
        args = parse_args([])
        assert args.command is None

    def test_consolidate_markdown_command(self):
        """Test parsing the consolidate-markdown command."""
        args = parse_args(["consolidate-markdown"])
        assert args.command == "consolidate-markdown"
        assert args.config == "config/consolidate-markdown.toml"

    def test_consolidate_markdown_command_with_config(self):
        """Test parsing the consolidate-markdown command with a custom config."""
        args = parse_args(["consolidate-markdown", "--config", "custom-config.toml"])
        assert args.command == "consolidate-markdown"
        assert args.config == "custom-config.toml"

    def test_upload_markdown_command(self):
        """Test parsing the upload-markdown command."""
        args = parse_args(["upload-markdown"])
        assert args.command == "upload-markdown"
        assert args.config == "config.toml"
        assert args.output_dir == "output"
        assert not args.dry_run

    def test_upload_markdown_command_with_options(self):
        """Test parsing the upload-markdown command with custom options."""
        args = parse_args(
            [
                "upload-markdown",
                "--config",
                "custom-config.toml",
                "--output-dir",
                "custom-output",
                "--dry-run",
            ]
        )
        assert args.command == "upload-markdown"
        assert args.config == "custom-config.toml"
        assert args.output_dir == "custom-output"
        assert args.dry_run


class TestMainAsync:
    """Tests for the main_async function."""

    @patch("nova.cli.consolidate_markdown_command")
    @patch("nova.cli.setup_logging")
    async def test_consolidate_markdown_command(
        self, mock_setup_logging, mock_consolidate_command
    ):
        """Test the consolidate-markdown command."""
        # Mock the consolidate_markdown_command to be an AsyncMock
        mock_consolidate_command.return_value = None

        # Call main_async with the consolidate-markdown command
        exit_code = await main_async(["consolidate-markdown"])

        # Verify that setup_logging was called
        mock_setup_logging.assert_called_once()

        # Verify that consolidate_markdown_command was called with the correct arguments
        mock_consolidate_command.assert_called_once_with(
            "config/consolidate-markdown.toml"
        )

        # Verify that the exit code is 0 (success)
        assert exit_code == 0

    @patch("nova.cli.upload_markdown_command")
    @patch("nova.cli.load_config")
    @patch("nova.cli.setup_logging")
    async def test_upload_markdown_command(
        self, mock_setup_logging, mock_load_config, mock_upload_command
    ):
        """Test the upload-markdown command."""
        # Mock the upload_markdown_command to be an AsyncMock
        mock_upload_command.return_value = None

        # Mock the load_config function
        mock_config = MagicMock()
        mock_config.logging.level = "INFO"
        mock_load_config.return_value = mock_config

        # Call main_async with the upload-markdown command
        exit_code = await main_async(["upload-markdown"])

        # Verify that load_config was called with the correct arguments
        mock_load_config.assert_called_once()

        # Verify that setup_logging was called with the correct arguments
        mock_setup_logging.assert_called_once_with(level="INFO")

        # Verify that upload_markdown_command was called with the correct arguments
        mock_upload_command.assert_called_once_with("config.toml", "output", False)

        # Verify that the exit code is 0 (success)
        assert exit_code == 0

    @patch("nova.cli.parse_args")
    async def test_no_command(self, mock_parse_args):
        """Test main_async with no command."""
        # Mock the parse_args function to return a namespace with no command
        mock_args = argparse.Namespace(command=None)
        mock_parse_args.return_value = mock_args

        # Call main_async with no command
        exit_code = await main_async([])

        # Verify that the exit code is 1 (error)
        assert exit_code == 1

    @patch("nova.cli.consolidate_markdown_command")
    @patch("nova.cli.setup_logging")
    async def test_configuration_error(
        self, mock_setup_logging, mock_consolidate_command
    ):
        """Test handling of a ConfigurationError."""
        # Mock the consolidate_markdown_command to raise a ConfigurationError
        mock_consolidate_command.side_effect = ConfigurationError(
            "Configuration error", config_file="config.toml", exit_code=2
        )

        # Call main_async with the consolidate-markdown command
        exit_code = await main_async(["consolidate-markdown"])

        # Verify that the exit code is 2 (from the ConfigurationError)
        assert exit_code == 2

    @patch("nova.cli.consolidate_markdown_command")
    @patch("nova.cli.setup_logging")
    async def test_nova_error(self, mock_setup_logging, mock_consolidate_command):
        """Test handling of a NovaError."""
        # Mock the consolidate_markdown_command to raise a NovaError
        mock_consolidate_command.side_effect = NovaError("Nova error", exit_code=3)

        # Call main_async with the consolidate-markdown command
        exit_code = await main_async(["consolidate-markdown"])

        # Verify that the exit code is 3 (from the NovaError)
        assert exit_code == 3

    @patch("nova.cli.consolidate_markdown_command")
    @patch("nova.cli.setup_logging")
    async def test_unexpected_error(self, mock_setup_logging, mock_consolidate_command):
        """Test handling of an unexpected error."""
        # Mock the consolidate_markdown_command to raise an unexpected error
        mock_consolidate_command.side_effect = Exception("Unexpected error")

        # Call main_async with the consolidate-markdown command
        exit_code = await main_async(["consolidate-markdown"])

        # Verify that the exit code is 1 (general error)
        assert exit_code == 1


class TestMain:
    """Tests for the main function."""

    @patch("nova.cli.main_async", new_callable=AsyncMock)
    @patch("asyncio.run")
    def test_main_success(self, mock_asyncio_run, mock_main_async):
        """Test the main function with a successful execution."""
        # Set up the mock for asyncio.run to return 0
        mock_asyncio_run.return_value = 0

        # Call main
        exit_code = main([])

        # Verify that asyncio.run was called once
        mock_asyncio_run.assert_called_once()

        # Verify that main_async was called with the correct arguments
        mock_main_async.assert_called_once_with([])

        # Verify that the exit code is 0 (success)
        assert exit_code == 0

    @patch("nova.cli.main_async")
    @patch("asyncio.run", side_effect=KeyboardInterrupt)
    def test_keyboard_interrupt(self, mock_asyncio_run, mock_main_async):
        """Test handling of a KeyboardInterrupt."""
        # Create a mock coroutine
        mock_coro = MagicMock()
        mock_main_async.return_value = mock_coro

        # Call main
        exit_code = main([])

        # Verify that main_async was called
        mock_main_async.assert_called_once_with([])

        # Verify that the exit code is 130 (SIGINT)
        assert exit_code == 130

    @patch("nova.cli.main_async")
    @patch("asyncio.run", side_effect=Exception("Unexpected error"))
    def test_unexpected_error(self, mock_asyncio_run, mock_main_async):
        """Test handling of an unexpected error."""
        # Create a mock coroutine
        mock_coro = MagicMock()
        mock_main_async.return_value = mock_coro

        # Call main
        exit_code = main([])

        # Verify that main_async was called
        mock_main_async.assert_called_once_with([])

        # Verify that the exit code is 1 (general error)
        assert exit_code == 1
