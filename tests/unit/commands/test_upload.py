"""
Unit tests for the upload command.

This module tests the upload-markdown command handler.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nova.commands.upload import upload_markdown_command
from nova.config.models import GraphlitConfig, MainConfig
from nova.exceptions import ConfigurationError, GraphlitClientError, UploadError


class TestUploadMarkdownCommand:
    """Tests for the upload_markdown_command function."""

    @patch("nova.commands.upload.load_config")
    @patch("graphlit.Graphlit")
    async def test_successful_upload(self, mock_graphlit, mock_load_config, tmp_path):
        """Test successful Markdown upload."""
        # Create a temporary configuration file
        config_file = tmp_path / "config.toml"
        config_file.touch()

        # Create a temporary output directory with a Markdown file
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        md_file = output_dir / "test.md"
        md_file.write_text("# Test Markdown")

        # Mock the configuration
        mock_config = MagicMock(spec=MainConfig)
        mock_config.graphlit = MagicMock(spec=GraphlitConfig)
        mock_config.graphlit.organization_id = "org123"
        mock_config.graphlit.environment_id = "env456"
        mock_config.graphlit.jwt_secret = "secret789"
        mock_load_config.return_value = mock_config

        # Mock the Graphlit client
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.ingest_text.id = "content123"
        mock_client.client.ingest_text.return_value = mock_response
        mock_graphlit.return_value = mock_client

        # Call the command
        await upload_markdown_command(str(config_file), str(output_dir), False)

        # Verify the configuration was loaded
        mock_load_config.assert_called_once_with(str(config_file.resolve()), MainConfig)

        # Verify Graphlit was initialized with the correct configuration
        mock_graphlit.assert_called_once_with(
            organization_id="org123",
            environment_id="env456",
            jwt_secret="secret789",
        )

        # Verify the ingest_text method was called with the correct parameters
        mock_client.client.ingest_text.assert_called_once_with(
            name="test.md",
            text="# Test Markdown",
            is_synchronous=True,
        )

    @patch("nova.commands.upload.load_config")
    @patch("graphlit.Graphlit")
    async def test_dry_run(self, mock_graphlit, mock_load_config, tmp_path):
        """Test dry run mode."""
        # Create a temporary configuration file
        config_file = tmp_path / "config.toml"
        config_file.touch()

        # Create a temporary output directory with a Markdown file
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        md_file = output_dir / "test.md"
        md_file.write_text("# Test Markdown")

        # Mock the configuration
        mock_config = MagicMock(spec=MainConfig)
        mock_config.graphlit = MagicMock(spec=GraphlitConfig)
        mock_config.graphlit.organization_id = "org123"
        mock_config.graphlit.environment_id = "env456"
        mock_config.graphlit.jwt_secret = "secret789"
        mock_load_config.return_value = mock_config

        # Call the command with dry_run=True
        await upload_markdown_command(str(config_file), str(output_dir), True)

        # Verify the configuration was loaded
        mock_load_config.assert_called_once_with(str(config_file.resolve()), MainConfig)

        # Verify Graphlit was initialized with the correct configuration
        mock_graphlit.assert_called_once_with(
            organization_id="org123",
            environment_id="env456",
            jwt_secret="secret789",
        )

        # Verify the ingest_text method was not called
        mock_graphlit.return_value.client.ingest_text.assert_not_called()

    @patch("nova.commands.upload.load_config")
    async def test_configuration_file_not_found(self, mock_load_config):
        """Test handling of a nonexistent configuration file."""
        # Mock the load_config function to raise FileNotFoundError
        mock_load_config.side_effect = FileNotFoundError("File not found")

        # Call the command and expect a ConfigurationError
        with pytest.raises(ConfigurationError) as excinfo:
            await upload_markdown_command("nonexistent.toml", "output", False)

        # Verify the error message
        assert "Configuration file not found" in str(excinfo.value)
        assert excinfo.value.config_file == str(Path("nonexistent.toml").resolve())

    @patch("nova.commands.upload.load_config")
    async def test_invalid_configuration(self, mock_load_config):
        """Test handling of an invalid configuration."""
        # Mock the load_config function to raise ValueError
        mock_load_config.side_effect = ValueError("Invalid configuration")

        # Call the command and expect a ConfigurationError
        with pytest.raises(ConfigurationError) as excinfo:
            await upload_markdown_command("invalid.toml", "output", False)

        # Verify the error message
        assert "Invalid configuration" in str(excinfo.value)
        assert excinfo.value.config_file == str(Path("invalid.toml").resolve())

    @patch("nova.commands.upload.load_config")
    @patch("graphlit.Graphlit", side_effect=ImportError("No module named 'graphlit'"))
    async def test_graphlit_import_error(
        self, mock_graphlit, mock_load_config, tmp_path
    ):
        """Test handling of an import error for the Graphlit library."""
        # Create a temporary configuration file
        config_file = tmp_path / "config.toml"
        config_file.touch()

        # Mock the configuration
        mock_config = MagicMock(spec=MainConfig)
        mock_config.graphlit = MagicMock(spec=GraphlitConfig)
        mock_config.graphlit.organization_id = "org123"
        mock_config.graphlit.environment_id = "env456"
        mock_config.graphlit.jwt_secret = "secret789"
        mock_load_config.return_value = mock_config

        # Call the command and expect an UploadError
        with pytest.raises(UploadError) as excinfo:
            await upload_markdown_command(str(config_file), "output", False)

        # Verify the error message
        assert "Graphlit client library not found" in str(excinfo.value)

    @patch("nova.commands.upload.load_config")
    @patch("graphlit.Graphlit")
    async def test_graphlit_initialization_error(
        self, mock_graphlit, mock_load_config, tmp_path
    ):
        """Test handling of an error during Graphlit initialization."""
        # Create a temporary configuration file
        config_file = tmp_path / "config.toml"
        config_file.touch()

        # Mock the configuration
        mock_config = MagicMock(spec=MainConfig)
        mock_config.graphlit = MagicMock(spec=GraphlitConfig)
        mock_config.graphlit.organization_id = "org123"
        mock_config.graphlit.environment_id = "env456"
        mock_config.graphlit.jwt_secret = "secret789"
        mock_load_config.return_value = mock_config

        # Mock the Graphlit constructor to raise an exception
        mock_graphlit.side_effect = Exception("Initialization error")

        # Call the command and expect a GraphlitClientError
        with pytest.raises(GraphlitClientError) as excinfo:
            await upload_markdown_command(str(config_file), "output", False)

        # Verify the error message
        assert "Error initializing Graphlit client" in str(excinfo.value)

    @patch("nova.commands.upload.load_config")
    @patch("graphlit.Graphlit")
    async def test_output_directory_not_found(
        self, mock_graphlit, mock_load_config, tmp_path
    ):
        """Test handling of a nonexistent output directory."""
        # Create a temporary configuration file
        config_file = tmp_path / "config.toml"
        config_file.touch()

        # Mock the configuration
        mock_config = MagicMock(spec=MainConfig)
        mock_config.graphlit = MagicMock(spec=GraphlitConfig)
        mock_config.graphlit.organization_id = "org123"
        mock_config.graphlit.environment_id = "env456"
        mock_config.graphlit.jwt_secret = "secret789"
        mock_load_config.return_value = mock_config

        # Call the command with a nonexistent output directory
        nonexistent_dir = tmp_path / "nonexistent"
        with pytest.raises(UploadError) as excinfo:
            await upload_markdown_command(str(config_file), str(nonexistent_dir), False)

        # Verify the error message
        assert "Output directory not found" in str(excinfo.value)

    @patch("nova.commands.upload.load_config")
    @patch("graphlit.Graphlit")
    async def test_output_not_a_directory(
        self, mock_graphlit, mock_load_config, tmp_path
    ):
        """Test handling of an output path that is not a directory."""
        # Create a temporary configuration file
        config_file = tmp_path / "config.toml"
        config_file.touch()

        # Create a temporary file (not a directory)
        output_file = tmp_path / "output.txt"
        output_file.touch()

        # Mock the configuration
        mock_config = MagicMock(spec=MainConfig)
        mock_config.graphlit = MagicMock(spec=GraphlitConfig)
        mock_config.graphlit.organization_id = "org123"
        mock_config.graphlit.environment_id = "env456"
        mock_config.graphlit.jwt_secret = "secret789"
        mock_load_config.return_value = mock_config

        # Call the command with a file as the output directory
        with pytest.raises(UploadError) as excinfo:
            await upload_markdown_command(str(config_file), str(output_file), False)

        # Verify the error message
        assert "Not a directory" in str(excinfo.value)

    @patch("nova.commands.upload.load_config")
    @patch("graphlit.Graphlit")
    async def test_no_markdown_files(self, mock_graphlit, mock_load_config, tmp_path):
        """Test handling of an output directory with no Markdown files."""
        # Create a temporary configuration file
        config_file = tmp_path / "config.toml"
        config_file.touch()

        # Create a temporary output directory with no Markdown files
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Mock the configuration
        mock_config = MagicMock(spec=MainConfig)
        mock_config.graphlit = MagicMock(spec=GraphlitConfig)
        mock_config.graphlit.organization_id = "org123"
        mock_config.graphlit.environment_id = "env456"
        mock_config.graphlit.jwt_secret = "secret789"
        mock_load_config.return_value = mock_config

        # Call the command
        await upload_markdown_command(str(config_file), str(output_dir), False)

        # Verify the ingest_text method was not called
        mock_graphlit.return_value.client.ingest_text.assert_not_called()

    @patch("nova.commands.upload.load_config")
    @patch("graphlit.Graphlit")
    async def test_upload_error(self, mock_graphlit, mock_load_config, tmp_path):
        """Test handling of an error during upload."""
        # Create a temporary configuration file
        config_file = tmp_path / "config.toml"
        config_file.touch()

        # Create a temporary output directory with a Markdown file
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        md_file = output_dir / "test.md"
        md_file.write_text("# Test Markdown")

        # Mock the configuration
        mock_config = MagicMock(spec=MainConfig)
        mock_config.graphlit = MagicMock(spec=GraphlitConfig)
        mock_config.graphlit.organization_id = "org123"
        mock_config.graphlit.environment_id = "env456"
        mock_config.graphlit.jwt_secret = "secret789"
        mock_load_config.return_value = mock_config

        # Mock the Graphlit client to raise an exception during upload
        mock_client = AsyncMock()
        mock_client.client.ingest_text.side_effect = Exception("Upload error")
        mock_graphlit.return_value = mock_client

        # Call the command and expect an UploadError
        with pytest.raises(UploadError) as excinfo:
            await upload_markdown_command(str(config_file), str(output_dir), False)

        # Verify the error message
        assert "Error uploading" in str(excinfo.value)
        assert "Upload error" in str(excinfo.value)
        assert excinfo.value.file_path == str(md_file)

    @patch("nova.commands.upload.load_config")
    @patch("graphlit.Graphlit")
    async def test_upload_response_error(
        self, mock_graphlit, mock_load_config, tmp_path
    ):
        """Test handling of an error response during upload."""
        # Create a temporary configuration file
        config_file = tmp_path / "config.toml"
        config_file.touch()

        # Create a temporary output directory with a Markdown file
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        md_file = output_dir / "test.md"
        md_file.write_text("# Test Markdown")

        # Mock the configuration
        mock_config = MagicMock(spec=MainConfig)
        mock_config.graphlit = MagicMock(spec=GraphlitConfig)
        mock_config.graphlit.organization_id = "org123"
        mock_config.graphlit.environment_id = "env456"
        mock_config.graphlit.jwt_secret = "secret789"
        mock_load_config.return_value = mock_config

        # Mock the Graphlit client to return an invalid response
        mock_client = AsyncMock()
        mock_client.client.ingest_text.return_value = None
        mock_graphlit.return_value = mock_client

        # Call the command and expect an UploadError
        with pytest.raises(UploadError) as excinfo:
            await upload_markdown_command(str(config_file), str(output_dir), False)

        # Verify the error message
        assert "Failed to upload" in str(excinfo.value)
        assert excinfo.value.file_path == str(md_file)
