import re
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from nova.ingestion.bear import BearExportHandler
from nova.ingestion.types import Attachment, MarkdownCorpus, Note

@pytest.fixture
def sample_note_content():
    return """# Test Note
This is a test note with a #tag and a #nested/tag.

Here's an image: ![test image](test.jpg)
And another: ![](test.heic)
And a document: [test.docx](test.docx)<!-- {"embed":"true"} -->
"""

@pytest.fixture
def mock_export_dir(tmp_path, sample_note_content):
    # Create export directory structure
    export_dir = tmp_path / "bear_export"
    export_dir.mkdir()

    # Create test note
    note_path = export_dir / "test.md"
    note_path.write_text(sample_note_content)

    # Create note-specific directory with attachments
    note_dir = export_dir / "test"
    note_dir.mkdir()

    # Create mock attachments in note directory
    (note_dir / "test.jpg").touch()
    (note_dir / "test.heic").touch()
    (note_dir / "test.docx").touch()

    return export_dir

def test_bear_export_handler(mock_export_dir):
    """Test the Bear export handler with note-specific directories."""
    handler = BearExportHandler(mock_export_dir)
    corpus = handler.process_export()

    assert isinstance(corpus, MarkdownCorpus)
    assert len(corpus.notes) == 1

    note = corpus.notes[0]
    assert note.title == "Test Note"
    assert len(note.tags) == 2
    assert "tag" in note.tags
    assert "nested/tag" in note.tags

    # Check attachments
    assert len(note.attachments) == 3

    # Verify each attachment type
    attachments_by_type = {
        att.metadata["type"]: att for att in note.attachments
    }

    # Check image attachments
    jpg_image = next(att for att in note.attachments
                    if att.path.name == "test.jpg")
    assert jpg_image.metadata["type"] == "image"
    assert jpg_image.content_type == "image/jpeg"
    assert jpg_image.original_name == "test image"

    heic_image = next(att for att in note.attachments
                     if att.path.name == "test.heic")
    assert heic_image.metadata["type"] == "image"
    assert heic_image.content_type == "image/heic"
    assert heic_image.original_name == "Untitled"

    # Check embedded document
    docx = next(att for att in note.attachments
                if att.path.name == "test.docx")
    assert docx.metadata["type"] == "embed"
    assert docx.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert docx.original_name == "test.docx"

def test_bear_export_handler_no_attachments(tmp_path):
    """Test the Bear export handler with a note that has no attachments."""
    export_dir = tmp_path / "bear_export"
    export_dir.mkdir()

    # Create a note without attachments
    note_content = """# Simple Note
This is a note without any attachments.
Just some #tags here."""

    note_path = export_dir / "simple.md"
    note_path.write_text(note_content)

    handler = BearExportHandler(export_dir)
    corpus = handler.process_export()

    assert len(corpus.notes) == 1
    note = corpus.notes[0]
    assert note.title == "Simple Note"
    assert len(note.tags) == 1
    assert "tags" in note.tags
    assert len(note.attachments) == 0

def test_bear_export_handler_missing_attachments(tmp_path):
    """Test the Bear export handler with missing referenced attachments."""
    export_dir = tmp_path / "bear_export"
    export_dir.mkdir()

    # Create a note referencing non-existent attachments
    note_content = """# Missing Attachments
Here's a missing image: ![missing](missing.jpg)
And a missing document: [doc](missing.pdf)<!-- {"embed":"true"} -->"""

    note_path = export_dir / "missing.md"
    note_path.write_text(note_content)

    # Create empty note directory
    (export_dir / "missing").mkdir()

    handler = BearExportHandler(export_dir)
    corpus = handler.process_export()

    assert len(corpus.notes) == 1
    note = corpus.notes[0]
    assert note.title == "Missing Attachments"
    assert len(note.attachments) == 0  # No attachments should be processed

def test_bear_export_handler_multiple_notes(tmp_path):
    """Test the Bear export handler with multiple notes."""
    export_dir = tmp_path / "bear_export"
    export_dir.mkdir()

    # Create first note with attachments
    note1_content = """# Note 1
With an image: ![img](image1.jpg)"""
    note1_path = export_dir / "note1.md"
    note1_path.write_text(note1_content)
    note1_dir = export_dir / "note1"
    note1_dir.mkdir()
    (note1_dir / "image1.jpg").touch()

    # Create second note with different attachments
    note2_content = """# Note 2
With a document: [doc](doc1.pdf)<!-- {"embed":"true"} -->"""
    note2_path = export_dir / "note2.md"
    note2_path.write_text(note2_content)
    note2_dir = export_dir / "note2"
    note2_dir.mkdir()
    (note2_dir / "doc1.pdf").touch()

    handler = BearExportHandler(export_dir)
    corpus = handler.process_export()

    assert len(corpus.notes) == 2

    # Check first note
    note1 = next(n for n in corpus.notes if n.title == "Note 1")
    assert len(note1.attachments) == 1
    assert note1.attachments[0].metadata["type"] == "image"

    # Check second note
    note2 = next(n for n in corpus.notes if n.title == "Note 2")
    assert len(note2.attachments) == 1
    assert note2.attachments[0].metadata["type"] == "embed"

def test_bear_export_handler_invalid_note(tmp_path):
    """Test the Bear export handler with an invalid note file."""
    export_dir = tmp_path / "bear_export"
    export_dir.mkdir()

    # Create an invalid note file
    note_path = export_dir / "invalid.md"
    note_path.write_text("") # Empty file

    handler = BearExportHandler(export_dir)
    corpus = handler.process_export()

    assert len(corpus.notes) == 0  # Invalid note should be skipped
