"""Tests for the Bear parser module."""

import json
import os
import time
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from nova.bear_parser.parser import BearParser, BearParserError


@pytest.fixture
def note_dir(tmp_path):
    """Create a temporary directory for test notes."""
    note_dir = tmp_path / "notes"
    note_dir.mkdir()
    return note_dir


@pytest.fixture
def nova_dir(tmp_path):
    """Create a temporary .nova directory."""
    nova_dir = tmp_path / ".nova"
    return nova_dir


@pytest.fixture
def attachments_dir(note_dir):
    """Create a temporary directory for attachments."""
    attachments_dir = note_dir / "attachments"
    attachments_dir.mkdir()
    return attachments_dir


@pytest.fixture
def test_note(note_dir, attachments_dir):
    """Create a test note with metadata."""
    # Create test note
    note_file = note_dir / "test_note.md"
    note_file.write_text(
        "# Test Note\nThis is a test note with #tag1 and #tag2.\n```\n#not_a_tag\n```"
    )

    # Create test image
    image_file = attachments_dir / "test_image.png"
    image_file.write_bytes(b"dummy image data")

    # Create metadata
    metadata = {
        note_file.name: {
            "title": "Test Note",
            "creation_date": "2024-01-01T12:00:00Z",
            "modification_date": "2024-01-02T12:00:00Z",
            "tags": ["tag1", "tag2"],
            "attachments": [image_file.name],
        }
    }

    metadata_file = note_dir / "metadata.json"
    metadata_file.write_text(json.dumps(metadata))

    return note_file


@pytest.mark.asyncio
async def test_parse_note(test_note, nova_dir):
    """Test parsing a note."""
    # Create mock OCR model
    mock_model = AsyncMock()
    mock_model.process.return_value = ("High quality text", 75.0)

    with patch("nova.bear_parser.parser.TesseractOcrModel", return_value=mock_model):
        parser = BearParser(test_note.parent, nova_dir=nova_dir)
        note = await parser.parse_note(test_note.name)

        assert note.title == "Test Note"
        assert note.created_at == datetime(2024, 1, 1, 12, 0)
        assert note.modified_at == datetime(2024, 1, 2, 12, 0)
        assert note.tags == {"tag1", "tag2"}
        assert len(note.attachments) == 1
        assert note.attachments[0].path.name == "test_image.png"

        # Verify OCR results
        attachment = note.attachments[0]
        assert attachment.ocr_text == "High quality text"
        assert attachment.metadata.get("ocr_confidence") == 75.0
        assert attachment.metadata.get("ocr_status") == "success"

        # Verify .nova directory structure
        assert (nova_dir / "placeholders" / "ocr").exists()
        assert (nova_dir / "processing" / "ocr").exists()
        assert (nova_dir / "logs").exists()


@pytest.mark.asyncio
async def test_parse_directory(test_note, nova_dir):
    """Test parsing all notes in a directory."""
    # Create mock OCR model
    mock_model = AsyncMock()
    mock_model.process.return_value = ("High quality text", 75.0)

    with patch("nova.bear_parser.parser.TesseractOcrModel", return_value=mock_model):
        parser = BearParser(test_note.parent, nova_dir=nova_dir)
        notes = await parser.parse_directory()

        assert len(notes) == 1
        assert notes[0].title == "Test Note"
        assert notes[0].tags == {"tag1", "tag2"}


@pytest.mark.asyncio
async def test_attachment_processing(note_dir, attachments_dir, nova_dir):
    """Test processing attachments with OCR."""
    # Create test files
    note_file = note_dir / "test_note.md"
    note_file.write_text("Test note content")

    image_file = attachments_dir / "test_image.png"
    image_file.write_bytes(b"dummy image data")

    metadata = {
        note_file.name: {
            "title": "Test Note",
            "creation_date": "2024-01-01T12:00:00Z",
            "modification_date": "2024-01-02T12:00:00Z",
            "tags": [],
            "attachments": [image_file.name],
        }
    }

    metadata_file = note_dir / "metadata.json"
    metadata_file.write_text(json.dumps(metadata))

    # Create mock OCR model
    mock_model = AsyncMock()
    mock_model.process.return_value = ("High quality text", 75.0)

    # Test successful OCR
    with patch("nova.bear_parser.parser.TesseractOcrModel", return_value=mock_model):
        parser = BearParser(note_dir, nova_dir=nova_dir)
        note = await parser.parse_note(note_file.name)

        assert len(note.attachments) == 1
        attachment = note.attachments[0]
        assert attachment.ocr_text == "High quality text"
        assert attachment.metadata.get("ocr_confidence") == 75.0
        assert attachment.metadata.get("ocr_status") == "success"

        # Verify no placeholder was created
        assert not list((nova_dir / "placeholders" / "ocr").glob("*.json"))


@pytest.mark.asyncio
async def test_placeholder_generation(note_dir, attachments_dir, nova_dir):
    """Test placeholder generation for failed OCR."""
    # Create test files
    note_file = note_dir / "test_note.md"
    note_file.write_text("Test note content")

    image_file = attachments_dir / "test_image.png"
    image_file.write_bytes(b"dummy image data")

    metadata = {
        note_file.name: {
            "title": "Test Note",
            "creation_date": "2024-01-01T12:00:00Z",
            "modification_date": "2024-01-02T12:00:00Z",
            "tags": [],
            "attachments": [image_file.name],
        }
    }

    metadata_file = note_dir / "metadata.json"
    metadata_file.write_text(json.dumps(metadata))

    # Create mock OCR model that raises an error
    mock_model = AsyncMock()
    mock_model.process.side_effect = Exception("OCR processing failed")

    # Test OCR failure and placeholder generation
    with patch("nova.bear_parser.parser.TesseractOcrModel", return_value=mock_model):
        parser = BearParser(note_dir, nova_dir=nova_dir)
        with pytest.raises(BearParserError) as exc_info:
            await parser.parse_note(note_file.name)

        assert "OCR processing failed" in str(exc_info.value)

        # Verify placeholder was created
        placeholder_files = list((nova_dir / "placeholders" / "ocr").glob("*.json"))
        assert len(placeholder_files) == 1

        # Verify placeholder content
        placeholder = json.loads(placeholder_files[0].read_text())
        assert placeholder["type"] == "ocr_failure"
        assert placeholder["version"] == 1
        assert placeholder["original_file"] == str(image_file)
        assert placeholder["ocr_status"] == "error"
        assert "error" in placeholder


@pytest.mark.asyncio
async def test_cleanup_placeholders(note_dir, nova_dir):
    """Test cleaning up old placeholder files."""
    parser = BearParser(note_dir, nova_dir=nova_dir)

    # Create test placeholder files
    placeholders_dir = nova_dir / "placeholders" / "ocr"
    placeholders_dir.mkdir(parents=True, exist_ok=True)

    # Create an old placeholder file
    old_placeholder = placeholders_dir / "old_placeholder.json"
    old_placeholder.write_text("{}")
    old_time = time.time() - (31 * 24 * 60 * 60)  # 31 days old
    os.utime(old_placeholder, (old_time, old_time))

    # Create a new placeholder file
    new_placeholder = placeholders_dir / "new_placeholder.json"
    new_placeholder.write_text("{}")

    # Run cleanup
    parser.cleanup_placeholders(max_age_days=30)

    # Verify old placeholder was removed and new one remains
    assert not old_placeholder.exists()
    assert new_placeholder.exists()
