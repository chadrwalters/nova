"""Unit tests for Nova finalize phase."""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from nova.config.settings import APIConfig, CacheConfig, NovaConfig, OpenAIConfig
from nova.core.metadata import FileMetadata
from nova.phases.finalize import FinalizePhase


@pytest.fixture
def nova_config(mock_fs):
    """Create test configuration."""
    config = NovaConfig(
        base_dir=str(mock_fs["root"]),
        input_dir=str(mock_fs["input"]),
        output_dir=str(mock_fs["output"]),
        processing_dir=str(mock_fs["processing"]),
        cache=CacheConfig(dir=str(mock_fs["cache"]), enabled=True, ttl=3600),
        apis=APIConfig(
            openai=OpenAIConfig(api_key="test_key", model="gpt-4o", max_tokens=300)
        ),
    )
    return config


@pytest.fixture
def mock_pipeline(mock_fs, nova_config):
    """Create a mock pipeline."""
    pipeline = MagicMock()
    pipeline.name = "test"
    pipeline.state = {
        "finalize": {
            "successful_files": set(),
            "failed_files": set(),
            "stats": {
                "total_files": 0,
                "failed_files": 0,
                "completed": False,
                "success": False,
            },
        }
    }
    pipeline.output_manager = MagicMock()
    pipeline.output_manager.get_output_path_for_phase.return_value = (
        mock_fs["output"] / "test.md"
    )
    pipeline.config = nova_config
    pipeline.get_phase_output_dir.return_value = mock_fs["output"]
    return pipeline


@pytest.fixture
def test_state(nova_config, mock_pipeline):
    """Create test state."""
    return {"config": nova_config, "pipeline": mock_pipeline}


@pytest.fixture
def split_dir(mock_fs):
    """Create and return the split phase directory with test files."""
    split_dir = mock_fs["processing"] / "phases" / "split"
    split_dir.mkdir(parents=True, exist_ok=True)

    # Create test files
    (split_dir / "Summary.md").write_text("# Test Document\nSummary content")
    (split_dir / "Raw Notes.md").write_text("Raw notes content")
    (split_dir / "Attachments.md").write_text("[ATTACH:PDF:test]")

    return split_dir


@pytest.mark.unit
@pytest.mark.phases
@pytest.mark.asyncio
class TestFinalizePhase:
    """Test finalize phase functionality."""

    async def test_basic_finalization(self, mock_fs, test_state, split_dir):
        """Test basic document finalization."""
        # Set up finalize phase
        phase = FinalizePhase(test_state["config"], test_state["pipeline"])

        # Process each file from split phase
        for file_path in split_dir.glob("*.md"):
            result = await phase.process_impl(file_path, mock_fs["output"])
            assert result is not None
            assert result.processed is True
            assert str(result.file_path) == str(file_path)

            # Verify file was copied to output
            output_path = mock_fs["output"] / file_path.name
            assert output_path.exists()
            assert output_path.read_text() == file_path.read_text()

            # Verify metadata file was created
            metadata_path = mock_fs["output"] / f"{file_path.stem}.metadata.json"
            assert metadata_path.exists()

    async def test_attachment_handling(self, mock_fs, test_state, split_dir):
        """Test handling of document attachments."""
        # Create test attachment files
        attachments_dir = split_dir / "attachments"
        attachments_dir.mkdir(parents=True)
        (attachments_dir / "test.pdf").write_text("PDF content")
        (attachments_dir / "image.png").write_bytes(b"PNG content")

        # Update Attachments.md to reference the test files
        attachments_md = split_dir / "Attachments.md"
        attachments_md.write_text(
            """# Attachments
        
[ATTACH:PDF:test]
[ATTACH:IMAGE:image]"""
        )

        # Set up finalize phase
        phase = FinalizePhase(test_state["config"], test_state["pipeline"])

        # Process attachments file
        result = await phase.process_impl(attachments_md, mock_fs["output"])
        assert result is not None
        assert result.processed is True

        # Verify attachments were copied
        output_attachments = mock_fs["output"] / "Attachments.md"
        assert output_attachments.exists()
        assert "[ATTACH:PDF:test]" in output_attachments.read_text()
        assert "[ATTACH:IMAGE:image]" in output_attachments.read_text()

        # Verify metadata file was created
        metadata_path = mock_fs["output"] / "Attachments.metadata.json"
        assert metadata_path.exists()

    async def test_metadata_consolidation(self, mock_fs, test_state, split_dir):
        """Test consolidation of metadata."""
        # Create test metadata
        metadata = FileMetadata.from_file(
            file_path=split_dir / "Summary.md",
            handler_name="finalize",
            handler_version="1.0",
        )
        metadata.title = "Test Document"
        metadata.metadata["tags"] = ["test", "document"]

        # Write initial metadata file
        metadata_file = split_dir / "Summary.metadata.json"
        metadata_file.write_text(
            json.dumps(
                {
                    "title": "Test Document",
                    "metadata": {
                        "tags": ["test", "document"],
                        "file_name": "Summary.md",
                        "file_path": str(split_dir / "Summary.md"),
                        "file_type": "md",
                        "handler_name": "finalize",
                        "handler_version": "1.0",
                    },
                    "processed": False,
                }
            )
        )

        # Set up finalize phase
        phase = FinalizePhase(test_state["config"], test_state["pipeline"])

        # Process file with metadata
        result = await phase.process_impl(
            split_dir / "Summary.md", mock_fs["output"], metadata
        )

        # Verify metadata was preserved and updated
        assert result is not None
        assert result.processed is True
        assert result.title == "Test Document"
        assert result.metadata["tags"] == ["test", "document"]
        assert len(result.output_files) > 0

        # Verify metadata file was created
        output_metadata_file = mock_fs["output"] / "Summary.metadata.json"
        assert output_metadata_file.exists()

        # Verify metadata content
        metadata_content = json.loads(output_metadata_file.read_text())
        assert metadata_content["title"] == "Test Document"
        assert metadata_content["metadata"]["tags"] == ["test", "document"]
        assert metadata_content["processed"] is True

    async def test_error_handling(self, mock_fs, test_state, split_dir):
        """Test error handling during finalization."""
        # Create an invalid file
        invalid_file = split_dir / "invalid.md"
        invalid_file.write_text("Invalid content")

        # Set up finalize phase
        phase = FinalizePhase(test_state["config"], test_state["pipeline"])

        # Mock shutil.copy2 to raise an error
        with patch("shutil.copy2", side_effect=OSError("Permission denied")):
            # Process invalid file
            result = await phase.process_impl(invalid_file, mock_fs["output"])

            # Verify error was handled
            assert result is None  # Should return None on failure

            # Verify pipeline state was updated
            assert str(invalid_file) in [
                str(f) for f in test_state["pipeline"].state["finalize"]["failed_files"]
            ]
