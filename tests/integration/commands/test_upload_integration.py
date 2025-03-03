"""
Integration tests for the upload-markdown command.

This module tests the end-to-end functionality of the upload-markdown command.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import toml

from nova.cli import main


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory with Markdown files."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Create some Markdown files
    (output_dir / "file1.md").write_text("# File 1\n\nThis is file 1.")
    (output_dir / "file2.md").write_text("# File 2\n\nThis is file 2.")

    # Create a subdirectory with more Markdown files
    subdir = output_dir / "subdir"
    subdir.mkdir()
    (subdir / "file3.md").write_text("# File 3\n\nThis is file 3.")

    # Create a non-Markdown file
    (output_dir / "not-markdown.txt").write_text("This is not a Markdown file.")

    return output_dir


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary configuration file for the upload-markdown command."""
    config_file = tmp_path / "config.toml"

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


class MockResponse:
    """Mock response from the Graphlit API."""

    def __init__(self, content_id=None):
        self.ingest_text = MagicMock() if content_id else None
        if content_id:
            self.ingest_text.id = content_id


class TestUploadMarkdownIntegration:
    """Integration tests for the upload-markdown command."""

    @patch("graphlit.Graphlit")
    def test_successful_upload(self, mock_graphlit, temp_config_file, temp_output_dir):
        """Test successful execution of the upload-markdown command."""
        # Mock the Graphlit client
        mock_client = AsyncMock()
        mock_response = MockResponse(content_id="test-content-id")
        mock_client.client.ingest_text.return_value = mock_response
        mock_graphlit.return_value = mock_client

        # Run the command
        result = main(
            [
                "upload-markdown",
                "--config",
                str(temp_config_file),
                "--output-dir",
                str(temp_output_dir),
            ]
        )

        # Verify the command was successful
        assert result == 0

        # Verify the Graphlit client was initialized with the correct configuration
        mock_graphlit.assert_called_once_with(
            organization_id="test-org-id",
            environment_id="test-env-id",
            jwt_secret="test-jwt-secret",
        )

        # Verify the ingest_text method was called for each Markdown file
        assert mock_client.client.ingest_text.call_count == 3  # 3 Markdown files

    @patch("graphlit.Graphlit")
    def test_dry_run(self, mock_graphlit, temp_config_file, temp_output_dir):
        """Test dry run mode."""
        # Mock the Graphlit client
        mock_client = AsyncMock()
        mock_graphlit.return_value = mock_client

        # Run the command with dry-run flag
        result = main(
            [
                "upload-markdown",
                "--config",
                str(temp_config_file),
                "--output-dir",
                str(temp_output_dir),
                "--dry-run",
            ]
        )

        # Verify the command was successful
        assert result == 0

        # Verify the Graphlit client was initialized
        mock_graphlit.assert_called_once()

        # Verify the ingest_text method was not called
        mock_client.client.ingest_text.assert_not_called()

    def test_nonexistent_config_file(self, temp_output_dir):
        """Test handling of a nonexistent configuration file."""
        # Run the command with a nonexistent configuration file
        result = main(
            [
                "upload-markdown",
                "--config",
                "nonexistent.toml",
                "--output-dir",
                str(temp_output_dir),
            ]
        )

        # Verify the command failed with the correct exit code
        assert result == 2  # ConfigurationError exit code

    @patch("graphlit.Graphlit", side_effect=ImportError("No module named 'graphlit'"))
    def test_graphlit_import_error(
        self, mock_graphlit, temp_config_file, temp_output_dir
    ):
        """Test handling of an import error for the Graphlit library."""
        # Run the command
        result = main(
            [
                "upload-markdown",
                "--config",
                str(temp_config_file),
                "--output-dir",
                str(temp_output_dir),
            ]
        )

        # Verify the command failed with the correct exit code
        assert result == 4  # UploadError exit code

    @patch("graphlit.Graphlit")
    def test_graphlit_initialization_error(
        self, mock_graphlit, temp_config_file, temp_output_dir
    ):
        """Test handling of an error during Graphlit initialization."""
        # Mock the Graphlit constructor to raise an exception
        mock_graphlit.side_effect = Exception("Initialization error")

        # Run the command
        result = main(
            [
                "upload-markdown",
                "--config",
                str(temp_config_file),
                "--output-dir",
                str(temp_output_dir),
            ]
        )

        # Verify the command failed with the correct exit code
        assert result == 5  # GraphlitClientError exit code

    def test_nonexistent_output_directory(self, temp_config_file, tmp_path):
        """Test handling of a nonexistent output directory."""
        # Run the command with a nonexistent output directory
        nonexistent_dir = tmp_path / "nonexistent"
        result = main(
            [
                "upload-markdown",
                "--config",
                str(temp_config_file),
                "--output-dir",
                str(nonexistent_dir),
            ]
        )

        # Verify the command failed with the correct exit code
        assert result == 4  # UploadError exit code

    def test_output_not_a_directory(self, temp_config_file, tmp_path):
        """Test handling of an output path that is not a directory."""
        # Create a file (not a directory)
        output_file = tmp_path / "output.txt"
        output_file.touch()

        # Run the command with a file as the output directory
        result = main(
            [
                "upload-markdown",
                "--config",
                str(temp_config_file),
                "--output-dir",
                str(output_file),
            ]
        )

        # Verify the command failed with the correct exit code
        assert result == 4  # UploadError exit code

    @patch("graphlit.Graphlit")
    def test_empty_output_directory(self, mock_graphlit, temp_config_file, tmp_path):
        """Test handling of an output directory with no Markdown files."""
        # Create an empty output directory
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        # Mock the Graphlit client
        mock_client = AsyncMock()
        mock_graphlit.return_value = mock_client

        # Run the command
        result = main(
            [
                "upload-markdown",
                "--config",
                str(temp_config_file),
                "--output-dir",
                str(empty_dir),
            ]
        )

        # Verify the command was successful
        assert result == 0

        # Verify the ingest_text method was not called
        mock_client.client.ingest_text.assert_not_called()

    @patch("graphlit.Graphlit")
    def test_upload_error(self, mock_graphlit, temp_config_file, temp_output_dir):
        """Test handling of an error during upload."""
        # Mock the Graphlit client to raise an exception during upload
        mock_client = AsyncMock()
        mock_client.client.ingest_text.side_effect = Exception("Upload error")
        mock_graphlit.return_value = mock_client

        # Run the command
        result = main(
            [
                "upload-markdown",
                "--config",
                str(temp_config_file),
                "--output-dir",
                str(temp_output_dir),
            ]
        )

        # Verify the command failed with the correct exit code
        assert result == 4  # UploadError exit code

    @patch("graphlit.Graphlit")
    def test_upload_response_error(
        self, mock_graphlit, temp_config_file, temp_output_dir
    ):
        """Test handling of an error response during upload."""
        # Mock the Graphlit client to return an invalid response
        mock_client = AsyncMock()
        mock_client.client.ingest_text.return_value = None
        mock_graphlit.return_value = mock_client

        # Run the command
        result = main(
            [
                "upload-markdown",
                "--config",
                str(temp_config_file),
                "--output-dir",
                str(temp_output_dir),
            ]
        )

        # Verify the command failed with the correct exit code
        assert result == 4  # UploadError exit code
