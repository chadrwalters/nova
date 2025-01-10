from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch
import subprocess

import pytest

from nova.ingestion.bear import BearExportHandler
from nova.ingestion.converter import DoclingConverter
from nova.ingestion.types import Attachment, MarkdownCorpus, Note

@pytest.fixture
def sample_note_content():
    return """# Test Note
This is a test note with a #tag and a #nested/tag.

Here's an image: ![test image](assets/test.png)
And a document: ![doc](assets/test.pdf)
"""

@pytest.fixture
def mock_export_dir(tmp_path, sample_note_content):
    # Create export directory structure
    export_dir = tmp_path / "bear_export"
    export_dir.mkdir()
    (export_dir / "assets").mkdir()
    
    # Create test files
    note_path = export_dir / "test.md"
    note_path.write_text(sample_note_content)
    
    # Create mock attachments
    (export_dir / "assets" / "test.png").touch()
    (export_dir / "assets" / "test.pdf").touch()
    
    return export_dir

def test_bear_export_handler(mock_export_dir):
    handler = BearExportHandler(mock_export_dir)
    corpus = handler.process_export()
    
    assert isinstance(corpus, MarkdownCorpus)
    assert len(corpus.notes) == 1
    
    note = corpus.notes[0]
    assert note.title == "Test Note"
    assert len(note.tags) == 2
    assert "tag" in note.tags
    assert "nested/tag" in note.tags
    assert len(note.attachments) == 2

@pytest.fixture
def sample_attachment():
    return Attachment(
        path=Path("test.pdf"),
        original_name="test",
        content_type="application/pdf"
    )

@patch("subprocess.run")
def test_docling_converter_success(mock_run, sample_attachment):
    # Mock successful conversion
    mock_run.return_value = Mock(
        returncode=0,
        stdout="Converted text",
        stderr=""
    )
    
    converter = DoclingConverter()
    
    success = converter.convert_attachment(sample_attachment)
    assert success
    assert sample_attachment.converted_text == "Converted text"
    assert sample_attachment.metadata["conversion_success"] == "true"
    
    mock_run.assert_called_once_with(
        ["docling", "convert", str(sample_attachment.path), "--format", "text"],
        capture_output=True,
        text=True,
        check=True
    )

@patch("subprocess.run")
def test_docling_converter_failure(mock_run, sample_attachment):
    # Mock failed conversion
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1,
        cmd=["docling", "convert"],
        stderr="Conversion failed"
    )
    
    converter = DoclingConverter()
    
    success = converter.convert_attachment(sample_attachment)
    assert not success
    assert sample_attachment.converted_text == "[Document: test]"
    assert sample_attachment.metadata["conversion_success"] == "false"
    assert sample_attachment.metadata["error"] == "Conversion failed" 