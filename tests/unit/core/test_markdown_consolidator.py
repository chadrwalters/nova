from pathlib import Path

import pytest

from src.core.markdown_consolidator import consolidate, consolidate_files


def test_consolidate_single_file(sample_markdown_file: Path, temp_output_dir: Path) -> None:
    """Test consolidating a single markdown file."""
    output_file = temp_output_dir / "output.md"
    media_dir = temp_output_dir / "_media"

    consolidate(
        input_path=sample_markdown_file.parent,
        output_file=output_file,
        recursive=False,
        verbose=True
    )

    assert output_file.exists()
    content = output_file.read_text()
    assert "# Test Document" in content
    assert "## Section 1" in content
    assert "## Section 2" in content


def test_consolidate_with_images(
    sample_markdown_file: Path,
    sample_image_file: Path,
    temp_output_dir: Path
) -> None:
    """Test consolidating markdown with image references."""
    # Modify the sample file to include an image reference
    content = sample_markdown_file.read_text()
    content += f"\n\n![Test Image]({sample_image_file.name})"
    sample_markdown_file.write_text(content)

    output_file = temp_output_dir / "output.md"
    media_dir = temp_output_dir / "_media"

    consolidate(
        input_path=sample_markdown_file.parent,
        output_file=output_file,
        recursive=False,
        verbose=True
    )

    assert output_file.exists()
    output_content = output_file.read_text()
    assert "![Test Image]" in output_content
    assert "_media" in output_content


def test_consolidate_multiple_files(test_data_dir: Path, temp_output_dir: Path) -> None:
    """Test consolidating multiple markdown files."""
    # Create multiple test files
    file1 = test_data_dir / "file1.md"
    file2 = test_data_dir / "file2.md"

    file1.write_text("# File 1\nContent 1")
    file2.write_text("# File 2\nContent 2")

    output_file = temp_output_dir / "output.md"
    media_dir = temp_output_dir / "_media"

    consolidate(
        input_path=test_data_dir,
        output_file=output_file,
        recursive=False,
        verbose=True
    )

    assert output_file.exists()
    content = output_file.read_text()
    assert "# File 1" in content
    assert "# File 2" in content
    assert "Content 1" in content
    assert "Content 2" in content

    # Cleanup
    file1.unlink()
    file2.unlink()


def test_empty_input_directory(temp_output_dir: Path) -> None:
    """Test consolidating an empty directory."""
    empty_dir = temp_output_dir / "empty"
    empty_dir.mkdir()
    output_file = temp_output_dir / "output.md"

    consolidate(
        input_path=empty_dir,
        output_file=output_file,
        recursive=False,
        verbose=True
    )

    assert not output_file.exists()


def test_invalid_input_directory(temp_output_dir: Path) -> None:
    """Test consolidating a non-existent directory."""
    output_file = temp_output_dir / "output.md"

    with pytest.raises(FileNotFoundError, match="Input directory not found"):
        consolidate(
            input_path=Path("nonexistent"),
            output_file=output_file,
            recursive=False,
            verbose=True
        )
