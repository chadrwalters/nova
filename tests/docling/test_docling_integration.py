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

    # Create nested directory structure
    nested_dir = input_dir / "nested" / "deep"
    nested_dir.mkdir(parents=True)
    nested_md = nested_dir / "nested.md"
    nested_md.write_text("# Nested Test\nThis is a nested test.")

    yield input_dir


def test_format_detection(test_files: Path) -> None:
    """Test format detection for various file types."""
    detector = FormatDetector()

    # Test markdown detection
    md_file = test_files / "test.md"
    md_format = detector.detect_format(md_file)
    assert md_format is not None
    assert md_format.name == "MD"

    # Test text detection
    txt_file = test_files / "test.txt"
    txt_format = detector.detect_format(txt_file)
    assert txt_format is not None
    assert txt_format.name == "TEXT"

    # Test HTML detection
    html_file = test_files / "test.html"
    html_format = detector.detect_format(html_file)
    assert html_format is not None
    assert html_format.name == "HTML"

    # Test markdown with frontmatter
    md_with_meta = test_files / "meta.md"
    md_with_meta.write_text(
        """---
title: Test
---
# Content"""
    )
    meta_format = detector.detect_format(md_with_meta)
    assert meta_format is not None
    assert meta_format.name == "MD"

    # Test text file with markdown content
    md_as_txt = test_files / "markdown.txt"
    md_as_txt.write_text("# Heading\n\nContent")
    txt_md_format = detector.detect_format(md_as_txt)
    assert txt_md_format is not None
    assert txt_md_format.name == "TEXT"  # Should detect as TEXT despite markdown content


def test_document_conversion(test_files: Path) -> None:
    """Test document conversion to markdown."""
    converter = DocumentConverter()
    detector = FormatDetector()

    # Convert HTML to markdown
    html_file = test_files / "test.html"
    html_format = detector.detect_format(html_file)
    assert html_format is not None

    html_doc = converter.convert(html_file, html_format)
    assert isinstance(html_doc, Document)
    assert "Test HTML" in html_doc.content
    assert "This is an HTML test." in html_doc.content

    # Convert text to markdown
    txt_file = test_files / "test.txt"
    txt_format = detector.detect_format(txt_file)
    assert txt_format is not None

    txt_doc = converter.convert(txt_file, txt_format)
    assert isinstance(txt_doc, Document)
    assert "Test Text" in txt_doc.content
    assert "This is a text test." in txt_doc.content

    # Convert nested markdown
    nested_file = test_files / "nested" / "deep" / "nested.md"
    nested_format = detector.detect_format(nested_file)
    assert nested_format is not None
    assert nested_format.name == "MD"

    nested_doc = converter.convert(nested_file, nested_format)
    assert isinstance(nested_doc, Document)
    assert "Nested Test" in nested_doc.content
    assert "This is a nested test." in nested_doc.content


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
version: 1.0.0
status: draft
category: documentation
priority: high
created: 2024-01-01
modified: 2024-01-15
---
# Test Content
This is a test."""

    md_file = test_files / "metadata.md"
    md_file.write_text(md_content)

    # Convert and check metadata
    md_format = detector.detect_format(md_file)
    assert md_format is not None

    doc = converter.convert(md_file, md_format)
    assert isinstance(doc, Document)
    assert doc.metadata is not None
    assert doc.metadata.get("title") == "Test Document"
    assert doc.metadata.get("author") == "Test Author"
    assert doc.metadata.get("date") == date(2024, 1, 15)  # YAML converts to date object
    assert doc.metadata.get("tags") == ["test", "docling"]
    assert doc.metadata.get("version") == "1.0.0"
    assert doc.metadata.get("status") == "draft"
    assert doc.metadata.get("category") == "documentation"
    assert doc.metadata.get("priority") == "high"
    assert doc.metadata.get("created") == date(2024, 1, 1)
    assert doc.metadata.get("modified") == date(2024, 1, 15)

    # Test HTML with metadata
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta name="author" content="Test Author">
    <meta name="date" content="2024-01-15">
    <title>Test HTML</title>
</head>
<body>
<h1>Test Content</h1>
<p>This is a test.</p>
</body>
</html>"""

    html_file = test_files / "metadata.html"
    html_file.write_text(html_content)

    html_format = detector.detect_format(html_file)
    assert html_format is not None

    html_doc = converter.convert(html_file, html_format)
    assert isinstance(html_doc, Document)
    assert html_doc.metadata is not None
    assert html_doc.metadata.get("title") == "Test HTML"
    assert html_doc.metadata.get("author") == "Test Author"
    assert html_doc.metadata.get("date") == "2024-01-15"


def test_process_notes_command(test_files: Path, tmp_path: Path) -> None:
    """Test the process-notes command with docling integration."""
    output_dir = tmp_path / "output"

    # Run command
    command = ProcessNotesCommand()
    command.run(input_dir=test_files, output_dir=output_dir)

    # Check output files and directory structure
    assert (output_dir / "test.md").exists()
    assert (output_dir / "test_text.md").exists()
    assert (output_dir / "test_html.md").exists()
    assert (output_dir / "nested" / "deep" / "nested.md").exists()

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

    nested_output = (output_dir / "nested" / "deep" / "nested.md").read_text()
    assert "Nested Test" in nested_output
    assert "This is a nested test." in nested_output


def test_process_notes_error_handling(test_files: Path, tmp_path: Path) -> None:
    """Test error handling in process-notes command."""
    output_dir = tmp_path / "output"
    command = ProcessNotesCommand()

    # Test with empty input directory
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    command.run(input_dir=empty_dir, output_dir=output_dir)
    assert not any(output_dir.iterdir())  # Output should be empty

    # Test with invalid file
    invalid_file = test_files / "invalid.xyz"
    invalid_file.write_text("Invalid content")
    command.run(input_dir=test_files, output_dir=output_dir)
    assert not (output_dir / "invalid.md").exists()  # Invalid file should be skipped

    # Test with unreadable file
    unreadable = test_files / "unreadable.txt"
    unreadable.write_text("Test content")
    unreadable.chmod(0o000)  # Make file unreadable
    command.run(input_dir=test_files, output_dir=output_dir)
    assert not (output_dir / "unreadable.md").exists()  # Unreadable file should be skipped
    unreadable.chmod(0o644)  # Restore permissions
