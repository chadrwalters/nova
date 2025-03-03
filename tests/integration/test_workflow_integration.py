"""
Integration tests for the end-to-end workflow.

This module tests the complete workflow of consolidating Markdown files and uploading them to Graphlit.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nova.cli import main


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary directory with configuration files."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create a consolidate-markdown config file
    consolidate_config = {
        "source": {
            "directory": str(tmp_path / "source"),
            "include_patterns": ["**/*.md"],
            "exclude_patterns": [],
        },
        "output": {
            "directory": str(tmp_path / "output"),
        },
        "logging": {
            "level": "INFO",
        },
    }

    with open(config_dir / "consolidate-markdown.toml", "w") as f:
        import toml

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
        import toml

        toml.dump(upload_config, f)

    return config_dir


@pytest.fixture
def temp_source_dir(tmp_path):
    """Create a temporary source directory with Markdown files."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    # Create a sample Markdown file
    sample_file = source_dir / "sample.md"
    sample_file.write_text("# Sample Markdown\n\nThis is a sample Markdown file.")

    return source_dir


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


class TestWorkflowIntegration:
    """Integration tests for the end-to-end workflow."""

    @patch("graphlit.Graphlit")
    @patch("consolidate_markdown.runner.Runner")
    @patch("nova.commands.consolidate.load_config")
    def test_complete_workflow(
        self,
        mock_load_config,
        mock_runner_class,
        mock_graphlit,
        temp_config_dir,
        temp_source_dir,
        temp_output_dir,
    ):
        """Test a complete workflow with all steps."""
        # Create a mock configuration with the nested structure
        from nova.config.models import (
            ConsolidateMarkdownConfig,
            ConsolidateMarkdownOutputConfig,
            ConsolidateMarkdownSourceConfig,
        )

        mock_source = MagicMock(spec=ConsolidateMarkdownSourceConfig)
        mock_source.directory = str(temp_source_dir)
        mock_source.include_patterns = ["**/*.md"]
        mock_source.exclude_patterns = []

        mock_output = MagicMock(spec=ConsolidateMarkdownOutputConfig)
        mock_output.directory = str(temp_output_dir)

        mock_config = MagicMock(spec=ConsolidateMarkdownConfig)
        mock_config.source = mock_source
        mock_config.output = mock_output

        mock_load_config.return_value = mock_config

        # Mock the Runner class
        mock_runner_instance = mock_runner_class.return_value
        mock_runner_instance.run = AsyncMock()

        # Create a sample output file to be uploaded
        output_file = temp_output_dir / "output.md"
        output_file.write_text(
            "# Output Markdown\n\nThis is a consolidated Markdown file."
        )

        # Step 1: Run the consolidate-markdown command
        result1 = main(
            [
                "consolidate-markdown",
                "--config",
                str(temp_config_dir / "consolidate-markdown.toml"),
            ]
        )

        # Verify the command was successful
        assert result1 == 0

        # Verify the Runner class was initialized with the correct configuration
        mock_runner_class.assert_called_once()

        # Verify run was called
        mock_runner_instance.run.assert_called_once()

        # Mock the Graphlit client
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.ingest_text = MagicMock()
        mock_response.ingest_text.id = "test-content-id"
        mock_client.client.ingest_text.return_value = mock_response
        mock_graphlit.return_value = mock_client

        # Step 2: Run the upload-markdown command
        result2 = main(
            [
                "upload-markdown",
                "--config",
                str(temp_config_dir / "upload-markdown.toml"),
                "--output-dir",
                str(temp_output_dir),
            ]
        )

        # Verify the command was successful
        assert result2 == 0

        # Verify the Graphlit client was initialized
        mock_graphlit.assert_called_once()

        # Verify the ingest_text method was called
        assert mock_client.client.ingest_text.call_count > 0

    @patch("graphlit.Graphlit")
    @patch("consolidate_markdown.runner.Runner")
    @patch("nova.commands.consolidate.load_config")
    def test_workflow_with_dry_run(
        self,
        mock_load_config,
        mock_runner_class,
        mock_graphlit,
        temp_config_dir,
        temp_source_dir,
        temp_output_dir,
    ):
        """Test a workflow with dry run enabled."""
        # Create a mock configuration with the nested structure
        from nova.config.models import (
            ConsolidateMarkdownConfig,
            ConsolidateMarkdownOutputConfig,
            ConsolidateMarkdownSourceConfig,
        )

        mock_source = MagicMock(spec=ConsolidateMarkdownSourceConfig)
        mock_source.directory = str(temp_source_dir)
        mock_source.include_patterns = ["**/*.md"]
        mock_source.exclude_patterns = []

        mock_output = MagicMock(spec=ConsolidateMarkdownOutputConfig)
        mock_output.directory = str(temp_output_dir)

        mock_config = MagicMock(spec=ConsolidateMarkdownConfig)
        mock_config.source = mock_source
        mock_config.output = mock_output

        mock_load_config.return_value = mock_config

        # Mock the Runner class
        mock_runner_instance = mock_runner_class.return_value
        mock_runner_instance.run = AsyncMock()

        # Create a sample output file to be uploaded
        output_file = temp_output_dir / "output.md"
        output_file.write_text(
            "# Output Markdown\n\nThis is a consolidated Markdown file."
        )

        # Step 1: Run the consolidate-markdown command
        result1 = main(
            [
                "consolidate-markdown",
                "--config",
                str(temp_config_dir / "consolidate-markdown.toml"),
            ]
        )

        # Verify the command was successful
        assert result1 == 0

        # Mock the Graphlit client
        mock_client = AsyncMock()
        mock_graphlit.return_value = mock_client

        # Step 2: Run the upload-markdown command with dry-run
        result2 = main(
            [
                "upload-markdown",
                "--config",
                str(temp_config_dir / "upload-markdown.toml"),
                "--output-dir",
                str(temp_output_dir),
                "--dry-run",
            ]
        )

        # Verify the command was successful
        assert result2 == 0

        # Verify the Graphlit client was initialized
        mock_graphlit.assert_called_once()

        # Verify the ingest_text method was not called
        mock_client.client.ingest_text.assert_not_called()

    @patch(
        "consolidate_markdown.runner.Runner",
        side_effect=Exception("Consolidation error"),
    )
    def test_workflow_with_consolidation_error(
        self, mock_runner_class, temp_config_dir, temp_source_dir, temp_output_dir
    ):
        """Test a workflow when consolidation fails."""
        # Step 1: Run the consolidate-markdown command
        result = main(
            [
                "consolidate-markdown",
                "--config",
                str(temp_config_dir / "consolidate-markdown.toml"),
            ]
        )

        # Verify the command failed with the correct exit code
        assert result != 0  # Non-zero exit code indicates failure

    @patch("consolidate_markdown.runner.Runner")
    @patch("graphlit.Graphlit", side_effect=Exception("Graphlit error"))
    def test_workflow_with_upload_error(
        self,
        mock_graphlit,
        mock_runner_class,
        temp_config_dir,
        temp_source_dir,
        temp_output_dir,
    ):
        """Test a workflow when upload fails."""
        # Mock the Runner class
        mock_runner_instance = mock_runner_class.return_value
        mock_runner_instance.run = AsyncMock()

        # Step 1: Run the consolidate-markdown command
        result1 = main(
            [
                "consolidate-markdown",
                "--config",
                str(temp_config_dir / "consolidate-markdown.toml"),
            ]
        )

        # Verify the command was successful
        assert result1 == 0

        # Step 2: Run the upload-markdown command
        result2 = main(
            [
                "upload-markdown",
                "--config",
                str(temp_config_dir / "upload-markdown.toml"),
                "--output-dir",
                str(temp_output_dir),
            ]
        )

        # Verify the command failed with a non-zero exit code
        assert result2 != 0
