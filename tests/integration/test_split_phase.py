"""Integration tests for the split phase."""

import os
import pytest
from pathlib import Path
import shutil
from textwrap import dedent

from nova.phases.split import SplitPhase
from nova.config.manager import ConfigManager


@pytest.fixture
def test_config(tmp_path):
    """Create a test configuration with temporary directories."""
    config = ConfigManager()
    
    # Set up temporary directories using update_config
    config.update_config({
        'base_dir': str(tmp_path),
        'input_dir': str(tmp_path / "input"),
        'output_dir': str(tmp_path / "output"),
        'processing_dir': str(tmp_path / "processing"),
        'cache': {
            'dir': str(tmp_path / "cache"),
            'enabled': True,
            'ttl': 3600
        }
    })
    
    # Create directories
    config.input_dir.mkdir(parents=True, exist_ok=True)
    config.processing_dir.mkdir(parents=True, exist_ok=True)
    
    return config


@pytest.fixture
def parse_dir(test_config):
    """Create a parse directory with test parsed markdown files."""
    parse_dir = test_config.processing_dir / "phases" / "parse"
    parse_dir.mkdir(parents=True)
    return parse_dir


def create_parsed_file(parse_dir: Path, name: str, content: str):
    """Helper to create a parsed markdown file."""
    file_path = parse_dir / f"{name}.parsed.md"
    file_path.write_text(content, encoding='utf-8')
    return file_path


@pytest.mark.asyncio
async def test_split_phase_basic(test_config, parse_dir):
    """Test basic split phase functionality with a simple file."""
    # Create a test parsed file
    content = dedent("""
    # Test Document
    
    This is a summary section.
    
    --==RAW NOTES==--
    These are raw notes.
    """).strip()
    
    create_parsed_file(parse_dir, "test", content)
    
    # Create a dummy input file to process
    input_file = test_config.input_dir / "test.txt"
    input_file.write_text("dummy content")
    
    # Run split phase
    split_phase = SplitPhase(test_config)
    split_dir = test_config.processing_dir / "phases" / "split"
    await split_phase.process(input_file, split_dir)
    
    # Check output files
    assert split_dir.exists()
    
    # Check Summary.md
    summary = (split_dir / "Summary.md").read_text(encoding='utf-8')
    assert "# Summary" in summary
    assert "## From test" in summary
    assert "This is a summary section" in summary
    
    # Check Raw Notes.md
    raw_notes = (split_dir / "Raw Notes.md").read_text(encoding='utf-8')
    assert "# Raw Notes" in raw_notes
    assert "## From test" in raw_notes
    assert "These are raw notes" in raw_notes


@pytest.mark.asyncio
async def test_split_phase_with_attachments(test_config, parse_dir):
    """Test split phase with a file containing attachments."""
    # Copy test files to input dir
    test_files_dir = Path(__file__).parent.parent / "data" / "attachments"
    shutil.copytree(test_files_dir, test_config.input_dir / "attachments")
    
    # Create a test parsed file with attachments
    content = dedent("""
    # Test Document with Attachments
    
    Here's an image:
    ![Test Image](../../../_NovaInput/attachments/png_test.png)
    
    And a PDF:
    * PDF: [Test PDF](../../../_NovaInput/attachments/pdf_test.pdf)
    
    --==RAW NOTES==--
    Raw notes with an image:
    ![Another Image](../../../_NovaInput/attachments/jpg_test.jpg)
    """).strip()
    
    create_parsed_file(parse_dir, "test_with_attachments", content)
    
    # Create a dummy input file to process
    input_file = test_config.input_dir / "test_with_attachments.txt"
    input_file.write_text("dummy content")
    
    # Run split phase
    split_phase = SplitPhase(test_config)
    split_dir = test_config.processing_dir / "phases" / "split"
    await split_phase.process(input_file, split_dir)
    
    # Check output files
    assert split_dir.exists()
    
    # Check Attachments.md
    attachments = (split_dir / "Attachments.md").read_text(encoding='utf-8')
    assert "# Attachments" in attachments
    assert "## From test_with_attachments" in attachments
    assert "* Image: [../../../_NovaInput/attachments/png_test.png]" in attachments
    assert "* PDF: [Test PDF]" in attachments
    assert "* Image: [../../../_NovaInput/attachments/jpg_test.jpg]" in attachments


@pytest.mark.asyncio
async def test_split_phase_multiple_files(test_config, parse_dir):
    """Test split phase with multiple files in different directories."""
    # Create test files in different subdirectories
    dir1 = parse_dir / "dir1"
    dir2 = parse_dir / "dir2"
    dir1.mkdir(parents=True)
    dir2.mkdir(parents=True)
    
    # File 1: Only summary
    content1 = dedent("""
    # Document 1
    This is just a summary document.
    No raw notes here.
    """).strip()
    create_parsed_file(dir1, "doc1", content1)
    
    # File 2: Summary and raw notes
    content2 = dedent("""
    # Document 2
    This is the summary.
    
    --==RAW NOTES==--
    These are raw notes.
    """).strip()
    create_parsed_file(dir2, "doc2", content2)
    
    # Create a dummy input file to process
    input_file = test_config.input_dir / "test_multiple.txt"
    input_file.write_text("dummy content")
    
    # Run split phase
    split_phase = SplitPhase(test_config)
    split_dir = test_config.processing_dir / "phases" / "split"
    await split_phase.process(input_file, split_dir)
    
    # Check output files
    assert split_dir.exists()
    
    # Check Summary.md
    summary = (split_dir / "Summary.md").read_text(encoding='utf-8')
    assert "## From dir1/doc1" in summary
    assert "## From dir2/doc2" in summary
    assert "This is just a summary document" in summary
    assert "This is the summary" in summary
    
    # Check Raw Notes.md
    raw_notes = (split_dir / "Raw Notes.md").read_text(encoding='utf-8')
    assert "## From dir2/doc2" in raw_notes
    assert "These are raw notes" in raw_notes
    # doc1 shouldn't be in raw notes
    assert "dir1/doc1" not in raw_notes


@pytest.mark.asyncio
async def test_split_phase_error_handling(test_config, parse_dir):
    """Test split phase error handling with invalid files."""
    # Create an unreadable file
    bad_file = create_parsed_file(parse_dir, "bad_file", "Some content")
    bad_file.chmod(0o000)  # Make file unreadable
    
    # Create a good file
    content = dedent("""
    # Good Document
    This is a good document.
    
    --==RAW NOTES==--
    With raw notes.
    """).strip()
    create_parsed_file(parse_dir, "good_file", content)
    
    # Create a dummy input file to process
    input_file = test_config.input_dir / "test_error.txt"
    input_file.write_text("dummy content")
    
    # Run split phase
    split_phase = SplitPhase(test_config)
    split_dir = test_config.processing_dir / "phases" / "split"
    await split_phase.process(input_file, split_dir)
    
    # Check output files
    assert split_dir.exists()
    
    # Check that good file was processed
    summary = (split_dir / "Summary.md").read_text(encoding='utf-8')
    assert "## From good_file" in summary
    
    # Clean up
    bad_file.chmod(0o644)  # Make file readable again for cleanup 