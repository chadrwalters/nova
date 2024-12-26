"""Test cases for markdown split processor."""

import pytest
from pathlib import Path
import os
import json
from datetime import datetime
from typing import Dict, Any

from nova.phases.split.processor import ThreeFileSplitProcessor
from nova.core.config import ProcessorConfig, PipelineConfig, PathConfig

@pytest.fixture
def test_files(tmp_path):
    """Create test files and directories."""
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()
    
    return {
        "input_dir": input_dir,
        "output_dir": output_dir
    }

@pytest.fixture
def processor(test_files):
    """Create processor instance with test configuration."""
    config = ProcessorConfig(
        name="markdown_split",
        description="Split markdown files into sections",
        processor="ThreeFileSplitProcessor",
        output_dir=str(test_files["output_dir"]),
        options={
            "section_files": ["summary.md", "raw_notes.md", "attachments.md"],
            "preserve_metadata": True,
            "track_relationships": True
        }
    )
    pipeline_config = PipelineConfig(
        paths=PathConfig(
            base_dir=str(test_files["input_dir"].parent)
        ),
        phases=[config],
        input_dir=str(test_files["input_dir"]),
        output_dir=str(test_files["output_dir"]),
        processing_dir=str(test_files["input_dir"] / "processing"),
        temp_dir=str(test_files["input_dir"] / "temp")
    )
    
    # Set up environment variables for test
    os.environ["NOVA_PHASE_MARKDOWN_AGGREGATE"] = str(test_files["input_dir"])
    os.environ["NOVA_PHASE_MARKDOWN_SPLIT"] = str(test_files["output_dir"])
    
    return ThreeFileSplitProcessor(processor_config=config, pipeline_config=pipeline_config)

def create_test_metadata():
    """Create test metadata with content markers."""
    return {
        'document': {
            'processor': 'MetadataManager',
            'version': '1.0',
            'timestamp': datetime.now().isoformat()
        },
        'content_markers': {
            'summary_blocks': [
                {'content': ['# Summary', 'Important summary content']},
                'Additional summary notes'
            ],
            'raw_notes_blocks': [
                {'content': ['# Raw Notes', 'Detailed note content']},
                'More raw notes'
            ],
            'attachment_blocks': [
                {'content': ['# Attachments', '[Doc 1](files/doc1.pdf)', '![Image 1](images/img1.png)']},
                '[Doc 2](files/doc2.pdf)'
            ]
        }
    }

async def test_metadata_based_splitting(processor, test_files):
    """Test splitting content based on metadata markers."""
    # Create test input file with metadata
    metadata = create_test_metadata()
    content = f"""<!--{json.dumps(metadata)}-->

# Test Document
Some content here
--==SUMMARY==--
# Summary
Important summary content
Additional summary notes

--==RAW NOTES==--
# Raw Notes
Detailed note content
More raw notes

--==ATTACHMENTS==--
# Attachments
[Doc 1](files/doc1.pdf)
![Image 1](images/img1.png)
[Doc 2](files/doc2.pdf)
"""
    
    input_file = test_files["input_dir"] / "all_merged_markdown.md"
    input_file.write_text(content)
    
    # Process the file
    await processor.setup()
    result = await processor.process()
    assert result.success
    
    # Check output files exist
    summary_file = test_files["output_dir"] / "summary.md"
    raw_notes_file = test_files["output_dir"] / "raw_notes.md"
    attachments_file = test_files["output_dir"] / "attachments.md"
    
    assert summary_file.exists()
    assert raw_notes_file.exists()
    assert attachments_file.exists()
    
    # Check content and metadata in each file
    summary_content = summary_file.read_text()
    assert '"processor": "ThreeFileSplitProcessor"' in summary_content
    assert '"section": "summary"' in summary_content
    assert 'Important summary content' in summary_content
    
    raw_notes_content = raw_notes_file.read_text()
    assert '"processor": "ThreeFileSplitProcessor"' in raw_notes_content
    assert '"section": "raw_notes"' in raw_notes_content
    assert 'Detailed note content' in raw_notes_content
    
    attachments_content = attachments_file.read_text()
    assert '"processor": "ThreeFileSplitProcessor"' in attachments_content
    assert '"section": "attachments"' in attachments_content
    assert '[Doc 1](files/doc1.pdf)' in attachments_content
    assert '![Image 1](images/img1.png)' in attachments_content

async def test_relationship_preservation(processor, test_files):
    """Test preservation of relationships in split files."""
    # Create test input file with relationships
    content = """<!--{
        "document": {
            "processor": "MetadataManager",
            "version": "1.0",
            "timestamp": "2024-01-01T00:00:00"
        },
        "relationships": {
            "attachments": [
                {"type": "image", "source": "doc1.md", "path": "images/img1.png", "alt_text": "Image 1"}
            ],
            "references": [
                {"type": "link", "source": "doc1.md", "target": "files/doc1.pdf", "text": "Document 1"}
            ]
        }
    }-->

--==SUMMARY==--
# Summary
See [Document 1](files/doc1.pdf)

--==RAW NOTES==--
# Notes
Reference to ![Image 1](images/img1.png)

--==ATTACHMENTS==--
# Attachments
- [Document 1](files/doc1.pdf)
- ![Image 1](images/img1.png)
"""
    
    input_file = test_files["input_dir"] / "all_merged_markdown.md"
    input_file.write_text(content)
    
    # Process the file
    await processor.setup()
    result = await processor.process()
    assert result.success
    
    # Check relationships in output files
    for section in ['summary', 'raw_notes', 'attachments']:
        content = (test_files["output_dir"] / f"{section}.md").read_text()
        metadata = json.loads(content[content.find('<!--')+4:content.find('-->')])
        
        # Verify relationships structure
        assert 'relationships' in metadata
        assert 'attachments' in metadata['relationships']
        assert 'references' in metadata['relationships']
        
        # Check specific relationships based on section
        if section == 'summary':
            assert any(r['target'] == 'files/doc1.pdf' for r in metadata['relationships']['references'])
        elif section == 'raw_notes':
            assert any(r['path'] == 'images/img1.png' for r in metadata['relationships']['attachments'])
        elif section == 'attachments':
            assert any(r['target'] == 'files/doc1.pdf' for r in metadata['relationships']['references'])
            assert any(r['path'] == 'images/img1.png' for r in metadata['relationships']['attachments'])

async def test_fallback_to_markers(processor, test_files):
    """Test fallback to marker-based splitting when metadata is missing."""
    content = """# Test Document

--==SUMMARY==--
# Summary
Important content

--==RAW NOTES==--
# Notes
Detailed notes

--==ATTACHMENTS==--
# Attachments
[Link](doc.pdf)
"""
    
    input_file = test_files["input_dir"] / "all_merged_markdown.md"
    input_file.write_text(content)
    
    # Process the file
    await processor.setup()
    result = await processor.process()
    assert result.success
    
    # Check content split correctly
    summary = (test_files["output_dir"] / "summary.md").read_text()
    assert "Important content" in summary
    
    notes = (test_files["output_dir"] / "raw_notes.md").read_text()
    assert "Detailed notes" in notes
    
    attachments = (test_files["output_dir"] / "attachments.md").read_text()
    assert "[Link](doc.pdf)" in attachments

async def test_error_handling(processor, test_files):
    """Test error handling for invalid input."""
    # Test with invalid metadata first
    input_file = test_files["input_dir"] / "all_merged_markdown.md"
    input_file.write_text("<!--{invalid json}-->\nContent")
    
    await processor.setup()
    result = await processor.process()
    assert not result.success
    assert len(result.errors) > 0
    assert "Failed to parse metadata" in result.errors[0]
    
    # Test with malformed content
    input_file.write_text("No metadata or markers\nJust some random content")
    
    result = await processor.process()
    assert result.success  # Should fall back to marker-based splitting
    assert len(result.processed_files) > 0  # Files should be created
    
    # Test with write permission error
    os.chmod(str(test_files["output_dir"]), 0o444)  # Make directory read-only
    try:
        result = await processor.process()
        assert not result.success
        assert len(result.errors) > 0
        assert "permission denied" in result.errors[0].lower()
    finally:
        os.chmod(str(test_files["output_dir"]), 0o755)  # Restore permissions
    
    # Clean up for missing file test
    input_file.unlink()
    result = await processor.process()
    assert result.success  # Missing file is not an error, just no work to do
    assert len(result.processed_files) == 0

async def test_empty_sections(processor, test_files):
    """Test handling of empty sections."""
    content = """<!--{
        "document": {
            "processor": "MetadataManager",
            "version": "1.0"
        },
        "content_markers": {
            "summary_blocks": [],
            "raw_notes_blocks": [],
            "attachment_blocks": []
        }
    }-->

--==SUMMARY==--

--==RAW NOTES==--

--==ATTACHMENTS==--
"""
    
    input_file = test_files["input_dir"] / "all_merged_markdown.md"
    input_file.write_text(content)
    
    # Process the file
    await processor.setup()
    result = await processor.process()
    assert result.success
    
    # Check that all files are created with metadata
    for section in ['summary', 'raw_notes', 'attachments']:
        file_path = test_files["output_dir"] / f"{section}.md"
        assert file_path.exists()
        content = file_path.read_text()
        assert '"processor": "ThreeFileSplitProcessor"' in content
        assert '"section": "' + section + '"' in content 