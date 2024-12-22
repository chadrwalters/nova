"""Tests for ThreeFileSplitProcessor."""

import os
from pathlib import Path
import pytest
from typing import Dict
import re

from nova.core.config import ProcessorConfig, NovaConfig, PathsConfig
from nova.core.errors import ProcessingError
from nova.processors.three_file_split_processor import ThreeFileSplitProcessor, ContentType

@pytest.fixture
def test_paths(tmp_path) -> PathsConfig:
    """Create test paths configuration."""
    base_dir = tmp_path / "nova"
    return PathsConfig(
        base_dir=base_dir,
        input_dir=base_dir / "input",
        output_dir=base_dir / "output",
        processing_dir=base_dir / "processing",
        temp_dir=base_dir / "temp",
        state_dir=base_dir / "state",
        phase_dirs={
            "markdown_parse": base_dir / "phases/parse",
            "markdown_consolidate": base_dir / "phases/consolidate",
            "markdown_aggregate": base_dir / "phases/aggregate",
            "markdown_split": base_dir / "phases/split"
        },
        image_dirs={
            "original": base_dir / "images/original",
            "processed": base_dir / "images/processed"
        },
        office_dirs={
            "temp": base_dir / "office/temp",
            "output": base_dir / "office/output"
        }
    )

@pytest.fixture
def test_config() -> ProcessorConfig:
    """Create test configuration."""
    return ProcessorConfig(
        enabled=True,
        options={
            "components": {
                "three_file_split_processor": {
                    "config": {
                        "output_files": {
                            "summary": "summary.md",
                            "raw_notes": "raw_notes.md",
                            "attachments": "attachments.md"
                        },
                        "section_markers": {
                            "summary": "---SUMMARY---",
                            "raw_notes": "---RAW NOTES---",
                            "attachments": "---ATTACHMENTS---"
                        },
                        "cross_linking": True,
                        "preserve_headers": True
                    }
                }
            }
        }
    )

@pytest.fixture
def processor(test_config, test_paths):
    """Create processor instance."""
    nova_config = NovaConfig(
        paths=test_paths,
        processors={"three_file_split": test_config}
    )
    return ThreeFileSplitProcessor(test_config, nova_config)

def test_split_content(processor, tmp_path):
    """Test splitting content into three files."""
    # Create test input file
    test_input = """# Test Document

--==SUMMARY==--
# Project Overview
This is a test summary section that provides a high-level overview.

## Key Points
- Point 1 with an image: ![Test Image 1](images/test1.png)
- Point 2 with reference to raw notes
- Point 3 with another image: ![Test Image 2](images/test2.jpg)

--==RAW NOTES==--
# Detailed Notes
These are the raw notes with more detailed information.

## Meeting Notes
- Discussed implementation details
- Referenced attachment: ![Architecture Diagram](diagrams/arch.png)
- More detailed points here

## Technical Specifications
1. Spec 1
2. Spec 2 with image: ![Tech Spec](images/spec.png)
3. Spec 3

--==ATTACHMENTS==--
# Project Attachments

## Images
![Test Image 1](images/test1.png)
This is the first test image showing the concept.

![Test Image 2](images/test2.jpg)
Second test image with implementation details.

## Diagrams
![Architecture Diagram](diagrams/arch.png)
System architecture overview diagram.

## Technical Documentation
![Tech Spec](images/spec.png)
Technical specification diagram."""
    
    input_path = tmp_path / "test_input.md"
    input_path.write_text(test_input)
    output_path = tmp_path / "output"
    
    # Process the file
    result_path = processor.process(input_path, output_path)
    
    # Verify output directory
    assert result_path.exists()
    assert result_path.is_dir()
    
    # Check output files exist
    summary_file = result_path / "summary.md"
    raw_notes_file = result_path / "raw_notes.md"
    attachments_file = result_path / "attachments.md"
    
    assert summary_file.exists()
    assert raw_notes_file.exists()
    assert attachments_file.exists()
    
    # Read output files
    summary_content = summary_file.read_text()
    raw_notes_content = raw_notes_file.read_text()
    attachments_content = attachments_file.read_text()
    
    # Verify content splitting
    assert "Project Overview" in summary_content
    assert "Detailed Notes" in raw_notes_content
    assert "Project Attachments" in attachments_content
    
    # Verify cross-linking
    assert "[Go to Raw Notes](raw_notes.md)" in summary_content
    assert "[Go to Attachments](attachments.md)" in summary_content
    assert "[Go to Summary](summary.md)" in raw_notes_content
    
    # Verify attachment references are updated
    assert "![Test Image 1](attachments.md#attachment-test1)" in summary_content
    assert "![Architecture Diagram](attachments.md#attachment-arch)" in raw_notes_content
    
    # Verify anchors in attachments
    assert '<a id="attachment-test1"></a>' in attachments_content
    assert '<a id="attachment-arch"></a>' in attachments_content

def test_error_handling(processor, tmp_path):
    """Test error handling for invalid input."""
    # Test with non-existent file
    input_path = Path("non_existent_file.md")
    output_path = tmp_path / "output"
    
    with pytest.raises(ProcessingError):
        processor.process(input_path, output_path)

def test_empty_content(processor, tmp_path):
    """Test handling of empty content."""
    # Create empty test file
    input_path = tmp_path / "empty.md"
    input_path.write_text("")
    output_path = tmp_path / "output"
    
    result_path = processor.process(input_path, output_path)
    
    # Verify empty files are created
    summary_file = result_path / "summary.md"
    raw_notes_file = result_path / "raw_notes.md"
    attachments_file = result_path / "attachments.md"
    
    assert summary_file.exists()
    assert raw_notes_file.exists()
    assert attachments_file.exists()
    
    # Verify files are empty or contain only cross-links
    summary_content = summary_file.read_text()
    assert "Project Overview" not in summary_content
    assert "[Go to Raw Notes](raw_notes.md)" in summary_content
    
def test_content_detection(processor):
    """Test content type detection logic."""
    # Test summary content detection
    summary_content = """
## Refined Thoughts
This is a refined analysis.

## Key Insights
- Important point 1
- Important point 2
"""
    assert processor.detect_content_type(summary_content) == ContentType.SUMMARY

    # Test raw notes content detection
    raw_notes_content = """
## Meeting Notes
Today we discussed the project timeline.

## Communication
Email from the team about deadlines.
"""
    assert processor.detect_content_type(raw_notes_content) == ContentType.RAW_NOTES

    # Test attachment content detection
    attachment_content = """
![Image](test.png)
[Document](report.pdf)
<!-- {"embed":"true"} -->
"""
    assert processor.detect_content_type(attachment_content) == ContentType.ATTACHMENTS

    # Test content with mixed markers but in summary section
    mixed_content = """
## Refined Thoughts
Analysis with an image ![test](image.png)
"""
    assert processor.detect_content_type(mixed_content, "SUMMARY") == ContentType.SUMMARY

def test_content_preservation(processor, tmp_path):
    """Test that no content is lost during splitting."""
    # Create test input with known size
    test_input = "A" * 1000 + "\n"  # Base content
    test_input += "--==SUMMARY==--\n"
    test_input += "## Refined Thoughts\n" + "B" * 2000 + "\n"  # Summary content
    test_input += "--==RAW NOTES==--\n"
    test_input += "## Meeting Notes\n" + "C" * 3000 + "\n"  # Raw notes content
    test_input += "--==ATTACHMENTS==--\n"
    test_input += "![Image](test.png)\n" + "D" * 1000 + "\n"  # Attachments content
    
    input_path = tmp_path / "test_input.md"
    input_path.write_text(test_input)
    output_path = tmp_path / "output"
    
    # Process the file
    result_path = processor.process(input_path, output_path)
    
    # Read output files
    summary_content = (result_path / "summary.md").read_text()
    raw_notes_content = (result_path / "raw_notes.md").read_text()
    attachments_content = (result_path / "attachments.md").read_text()
    
    # Verify content sizes
    input_size = len(test_input.encode('utf-8'))
    output_size = sum(
        len(content.encode('utf-8')) 
        for content in [summary_content, raw_notes_content, attachments_content]
    )
    
    # Allow for some size difference due to navigation links and formatting
    size_difference = abs(output_size - input_size)
    assert size_difference < 1000, "Content size changed significantly"
    
    # Verify all content is preserved
    assert "B" * 2000 in summary_content
    assert "C" * 3000 in raw_notes_content
    assert "D" * 1000 in attachments_content

def test_navigation_and_references(processor, tmp_path):
    """Test navigation links and reference updating."""
    test_input = """
--==SUMMARY==--
# Summary
## Refined Thoughts
See [[Meeting Notes]] for details.
![Design](design.png)
[Report](report.pdf)

--==RAW NOTES==--
# Raw Notes
## Meeting Notes
Reference to [[Refined Thoughts]]
![Architecture](arch.png)

--==ATTACHMENTS==--
# Attachments
![Design](design.png)
Design diagram showing the concept.

![Architecture](arch.png)
Architecture overview.

[Report](report.pdf)
Project report document.
"""
    
    input_path = tmp_path / "test_input.md"
    input_path.write_text(test_input)
    output_path = tmp_path / "output"
    
    # Process the file
    result_path = processor.process(input_path, output_path)
    
    # Read output files
    summary_content = (result_path / "summary.md").read_text()
    raw_notes_content = (result_path / "raw_notes.md").read_text()
    attachments_content = (result_path / "attachments.md").read_text()
    
    # Test navigation links
    assert "[Go to Raw Notes](raw_notes.md)" in summary_content
    assert "[Go to Attachments](attachments.md)" in summary_content
    assert "[Go to Summary](summary.md)" in raw_notes_content
    assert "[Go to Summary](summary.md)" in attachments_content
    
    # Test section references
    assert "raw_notes.md#meeting-notes" in summary_content
    assert "summary.md#refined-thoughts" in raw_notes_content
    
    # Test attachment references
    assert "attachments.md#" in summary_content
    assert "attachments.md#" in raw_notes_content
    
    # Test anchors in attachments
    assert '<a id="' in attachments_content
    
    # Verify bi-directional linking
    assert all(
        ref in summary_content 
        for ref in ["raw_notes.md", "attachments.md"]
    )
    assert all(
        ref in raw_notes_content 
        for ref in ["summary.md", "attachments.md"]
    )
    assert all(
        ref in attachments_content 
        for ref in ["summary.md", "raw_notes.md"]
    )

def test_large_file_handling(processor, tmp_path):
    """Test handling of large files (>400KB)."""
    # Create large test input
    large_content = "A" * 200_000  # Base content
    summary_content = "B" * 100_000  # Summary section
    raw_notes_content = "C" * 150_000  # Raw notes section
    attachments_content = "D" * 50_000  # Attachments section
    
    test_input = (
        large_content + "\n"
        "--==SUMMARY==--\n"
        "## Refined Thoughts\n" + summary_content + "\n"
        "--==RAW NOTES==--\n"
        "## Meeting Notes\n" + raw_notes_content + "\n"
        "--==ATTACHMENTS==--\n"
        "# Attachments\n" + attachments_content
    )
    
    input_path = tmp_path / "large_test.md"
    input_path.write_text(test_input)
    output_path = tmp_path / "output"
    
    # Process the file
    result_path = processor.process(input_path, output_path)
    
    # Verify files exist and have correct content
    summary_file = result_path / "summary.md"
    raw_notes_file = result_path / "raw_notes.md"
    attachments_file = result_path / "attachments.md"
    
    assert summary_file.exists()
    assert raw_notes_file.exists()
    assert attachments_file.exists()
    
    # Verify content sizes
    assert len(summary_file.read_text()) > 100_000
    assert len(raw_notes_file.read_text()) > 150_000
    assert len(attachments_file.read_text()) > 50_000
    
    # Verify processing completed without errors
    assert processor.stats['content_sizes']['input'] > 400_000
    total_output = sum(
        processor.stats['content_sizes'][key] 
        for key in ['summary', 'raw_notes', 'attachments']
    )
    assert total_output > 400_000
    