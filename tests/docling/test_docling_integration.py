"""Test docling integration with Nova."""
from collections.abc import Generator
from datetime import date
from pathlib import Path

import pytest

from nova.cli.commands.process_notes import ProcessNotesCommand
from nova.docling import Document, DocumentConverter, FormatDetector


@pytest.fixture
def test_files(tmp_path: Path) -> Generator[Path, None, None]:
    """Create test files in various formats."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    # Create markdown file with unique content
    md_file = input_dir / "test.md"
    md_file.write_text("# Test Markdown\nThis is a markdown test.")

    # Create text file with unique content
    txt_file = input_dir / "test.txt"
    txt_file.write_text("Test Text\nThis is a text test.")

    # Create HTML file with unique content
    html_file = input_dir / "test.html"
    html_file.write_text("<h1>Test HTML</h1><p>This is an HTML test.</p>")

    yield input_dir


def test_format_detection(test_files: Path) -> None:
    """Test format detection for various file types."""
    detector = FormatDetector()

    # Test markdown detection
    md_format = detector.detect_format(test_files / "test.md")
    assert md_format is not None
    assert md_format.name == "MD"

    # Test text detection
    txt_format = detector.detect_format(test_files / "test.txt")
    assert txt_format is not None
    assert txt_format.name == "TEXT"

    # Test HTML detection
    html_format = detector.detect_format(test_files / "test.html")
    assert html_format is not None
    assert html_format.name == "HTML"


def test_document_conversion(test_files: Path) -> None:
    """Test document conversion to markdown."""
    converter = DocumentConverter()
    detector = FormatDetector()

    # Convert HTML to markdown
    html_file = test_files / "test.html"
    html_format = detector.detect_format(html_file)
    assert html_format is not None

    html_doc = converter.convert_file(html_file, html_format)
    assert isinstance(html_doc, Document)
    assert "Test HTML" in html_doc.content
    assert "This is an HTML test." in html_doc.content

    # Convert text to markdown
    txt_file = test_files / "test.txt"
    txt_format = detector.detect_format(txt_file)
    assert txt_format is not None

    txt_doc = converter.convert_file(txt_file, txt_format)
    assert isinstance(txt_doc, Document)
    assert "Test Text" in txt_doc.content
    assert "This is a text test." in txt_doc.content


def test_metadata_preservation(test_files: Path) -> None:
    """Test metadata preservation during conversion."""
    converter = DocumentConverter()
    detector = FormatDetector()

    # Create markdown with metadata
    md_content = """---
title: Test Document
author: Test Author
date: 2024-01-15
tags: [test, docling]
---
# Test Content
This is a test."""

    md_file = test_files / "metadata.md"
    md_file.write_text(md_content)

    # Convert and check metadata
    md_format = detector.detect_format(md_file)
    assert md_format is not None

    doc = converter.convert_file(md_file, md_format)
    assert isinstance(doc, Document)
    assert doc.metadata is not None
    assert doc.metadata.get("title") == "Test Document"
    assert doc.metadata.get("author") == "Test Author"
    assert doc.metadata.get("date") == date(2024, 1, 15)  # YAML converts to date object
    assert doc.metadata.get("tags") == ["test", "docling"]


def test_process_notes_command(test_files: Path, tmp_path: Path) -> None:
    """Test the process-notes command with docling integration."""
    output_dir = tmp_path / "output"

    # Run command
    command = ProcessNotesCommand()
    command.run(input_dir=test_files, output_dir=output_dir)

    # Check output files
    assert (output_dir / "test.md").exists()
    assert (output_dir / "test_text.md").exists()
    assert (output_dir / "test_html.md").exists()

    # Check converted content
    html_output = (output_dir / "test_html.md").read_text()
    assert "Test HTML" in html_output
    assert "This is an HTML test." in html_output

    txt_output = (output_dir / "test_text.md").read_text()
    assert "Test Text" in txt_output
    assert "This is a text test." in txt_output

    md_output = (output_dir / "test.md").read_text()
    assert "Test Markdown" in md_output
    assert "This is a markdown test." in md_output
