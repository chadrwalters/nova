from datetime import datetime
from pathlib import Path

import pytest

from src.core.markdown_consolidator import (
    consolidate,
    extract_date_from_filename,
    process_file,
    process_image_links,
)


def test_extract_date_from_filename() -> None:
    """Test date extraction from filename."""
    # Test valid date
    assert extract_date_from_filename("20240101_test.md") == datetime(2024, 1, 1)

    # Test invalid date
    assert extract_date_from_filename("test.md") == datetime.fromtimestamp(0)


def test_process_image_links_with_base64(tmp_path: Path) -> None:
    """Test processing base64 encoded images in markdown content."""
    # Create test data
    media_dir = tmp_path / "_media"
    media_dir.mkdir()

    file_path = tmp_path / "test.md"
    content = (
        "# Test\n"
        "![Test Image](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1)"
    )

    # Process content
    processed_content, media_files = process_image_links(content, file_path, media_dir)

    # Verify results
    assert len(media_files) == 1
    assert media_files[0].parent == media_dir
    assert media_files[0].suffix == ".png"
    assert "![Test Image](_media/" in processed_content


def test_process_file(tmp_path: Path) -> None:
    """Test processing a markdown file."""
    # Create test file
    file_path = tmp_path / "20240101_test.md"
    file_path.write_text("# Test\nThis is a test file.")

    # Create media directory
    media_dir = tmp_path / "_media"
    media_dir.mkdir()

    # Process file
    result = process_file(file_path, media_dir)

    # Verify results
    assert result.path == file_path
    assert result.date == datetime(2024, 1, 1)
    assert result.content == "# Test\nThis is a test file."
    assert not result.media_files


def test_consolidate(tmp_path: Path) -> None:
    """Test consolidating markdown files."""
    # Create test files
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    (input_dir / "20240101_first.md").write_text("# First")
    (input_dir / "20240102_second.md").write_text("# Second")

    output_file = tmp_path / "output.md"

    # Consolidate files
    consolidate(input_dir, output_file)

    # Verify results
    assert output_file.exists()
    content = output_file.read_text()
    assert "# First" in content
    assert "# Second" in content
