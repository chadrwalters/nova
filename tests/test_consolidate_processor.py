#!/usr/bin/env python3

import os
import pytest
from pathlib import Path
from consolidate_processor import ConsolidateProcessor

@pytest.fixture
def setup_dirs(tmp_path):
    """Set up test directories."""
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    
    input_dir.mkdir()
    output_dir.mkdir()
    
    return input_dir, output_dir

@pytest.fixture
def create_test_files(setup_dirs):
    """Create test markdown files with attachments."""
    input_dir, _ = setup_dirs
    
    # Create test attachment
    attachment_content = "Test attachment content"
    attachment_file = input_dir / "test_attachment.txt"
    attachment_file.write_text(attachment_content)
    
    # Create markdown file with attachment block
    md_file = input_dir / "test.md"
    md_content = f"""# Test Document

This is a test document with an attachment.

--==ATTACHMENT_BLOCK: {str(attachment_file)}==--
{attachment_content}
--==ATTACHMENT_BLOCK_END==--
"""
    md_file.write_text(md_content)
    
    return md_file, attachment_file

def test_processor_initialization(setup_dirs):
    """Test consolidate processor initialization."""
    input_dir, output_dir = setup_dirs
    processor = ConsolidateProcessor(input_dir, output_dir)
    
    assert processor.input_dir == input_dir
    assert processor.output_dir == output_dir

def test_file_processing(setup_dirs, create_test_files):
    """Test processing a single markdown file."""
    input_dir, output_dir = setup_dirs
    md_file, attachment_file = create_test_files
    
    processor = ConsolidateProcessor(input_dir, output_dir)
    result = processor.process_file(md_file)
    
    assert result is not None
    assert result['input_file'] == str(md_file)
    assert result['output_file'] == str(output_dir / "test.md")
    assert result['attachments_dir'] == str(output_dir / "test_attachments")
    assert len(result['attachments']) == 1
    
    # Check that output files exist
    output_file = Path(result['output_file'])
    attachments_dir = Path(result['attachments_dir'])
    assert output_file.exists()
    assert attachments_dir.exists()
    assert (attachments_dir / attachment_file.name).exists()

def test_directory_processing(setup_dirs, create_test_files):
    """Test processing all markdown files in a directory."""
    input_dir, output_dir = setup_dirs
    
    processor = ConsolidateProcessor(input_dir, output_dir)
    success = processor.process_directory()
    
    assert success
    assert (output_dir / "test.md").exists()
    assert (output_dir / "test_attachments").exists()

def test_missing_attachment_handling(setup_dirs):
    """Test handling of missing attachments."""
    input_dir, output_dir = setup_dirs
    
    # Create markdown file with missing attachment
    md_file = input_dir / "missing.md"
    md_content = """# Test Document

--==ATTACHMENT_BLOCK: missing.txt==--
Missing content
--==ATTACHMENT_BLOCK_END==--
"""
    md_file.write_text(md_content)
    
    processor = ConsolidateProcessor(input_dir, output_dir)
    result = processor.process_file(md_file)
    
    assert result is not None
    assert len(result['attachments']) == 1
    assert result['attachments'][0]['new_path'] is None

def test_nested_directory_processing(setup_dirs):
    """Test processing markdown files in nested directories."""
    input_dir, output_dir = setup_dirs
    
    # Create nested directory structure
    nested_dir = input_dir / "nested" / "dir"
    nested_dir.mkdir(parents=True)
    
    # Create markdown file in nested directory
    md_file = nested_dir / "nested.md"
    md_content = """# Nested Test

--==ATTACHMENT_BLOCK: test.txt==--
Test content
--==ATTACHMENT_BLOCK_END==--
"""
    md_file.write_text(md_content)
    
    # Create attachment in nested directory
    attachment_file = nested_dir / "test.txt"
    attachment_file.write_text("Test content")
    
    processor = ConsolidateProcessor(input_dir, output_dir)
    success = processor.process_directory()
    
    assert success
    assert (output_dir / "nested" / "dir" / "nested.md").exists()
    assert (output_dir / "nested" / "dir" / "nested_attachments").exists()
    assert (output_dir / "nested" / "dir" / "nested_attachments" / "test.txt").exists()

def test_multiple_attachments(setup_dirs):
    """Test handling multiple attachments in a single file."""
    input_dir, output_dir = setup_dirs
    
    # Create test attachments
    attachment1 = input_dir / "attachment1.txt"
    attachment2 = input_dir / "attachment2.txt"
    attachment1.write_text("Content 1")
    attachment2.write_text("Content 2")
    
    # Create markdown file with multiple attachments
    md_file = input_dir / "multiple.md"
    md_content = f"""# Multiple Attachments

--==ATTACHMENT_BLOCK: {str(attachment1)}==--
Content 1
--==ATTACHMENT_BLOCK_END==--

--==ATTACHMENT_BLOCK: {str(attachment2)}==--
Content 2
--==ATTACHMENT_BLOCK_END==--
"""
    md_file.write_text(md_content)
    
    processor = ConsolidateProcessor(input_dir, output_dir)
    result = processor.process_file(md_file)
    
    assert result is not None
    assert len(result['attachments']) == 2
    assert all(attachment['new_path'] is not None for attachment in result['attachments'])

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 