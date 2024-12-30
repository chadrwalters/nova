"""Test split phase functionality."""

import pytest
import tempfile
from pathlib import Path
import shutil
import json
from nova.phases.split import SplitPhase
from nova.core.pipeline import NovaPipeline
from nova.config.manager import ConfigManager

@pytest.fixture
def temp_workspace():
    """Create temporary workspace."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir)
        input_dir = workspace / "input"
        output_dir = workspace / "output"
        processing_dir = workspace / "processing"
        
        # Create directories
        input_dir.mkdir()
        output_dir.mkdir()
        processing_dir.mkdir()
        
        # Create test files
        test_file = input_dir / "20240119-test.parsed.md"
        test_file.write_text("""# Test Document

--==SUMMARY==--
# Summary Section
This is a summary of the document.

Here's an image:
![Test Image](attachments/20240119/jpg/test.jpg)

And a document:
[Test Doc](attachments/20240119/doc/test.docx)

--==RAW NOTES==--
# Raw Notes Section
These are the raw notes.

Another image:
![Another Image](attachments/20240119/jpg/another.jpg)

--==ATTACHMENTS==--
## Images
- ![Test Image](attachments/20240119/jpg/test.jpg)
- ![Another Image](attachments/20240119/jpg/another.jpg)

## Documents
- [Test Doc](attachments/20240119/doc/test.docx)
""")
        
        # Create test attachments
        (input_dir / "attachments" / "20240119" / "jpg").mkdir(parents=True)
        (input_dir / "attachments" / "20240119" / "doc").mkdir(parents=True)
        
        # Create dummy image and doc files
        (input_dir / "attachments" / "20240119" / "jpg" / "test.jpg").write_bytes(b"test image")
        (input_dir / "attachments" / "20240119" / "jpg" / "another.jpg").write_bytes(b"another image")
        (input_dir / "attachments" / "20240119" / "doc" / "test.docx").write_bytes(b"test doc")
        
        yield {
            'workspace': workspace,
            'input_dir': input_dir,
            'output_dir': output_dir,
            'processing_dir': processing_dir
        }

@pytest.fixture
def config(temp_workspace):
    """Create test configuration."""
    config = ConfigManager()
    config.update_config({
        'base_dir': str(temp_workspace['workspace']),
        'input_dir': str(temp_workspace['input_dir']),
        'output_dir': str(temp_workspace['output_dir']),
        'processing_dir': str(temp_workspace['processing_dir']),
        'cache': {
            'dir': str(temp_workspace['workspace'] / 'cache'),
            'enabled': True,
            'ttl': 3600
        }
    })
    return config

@pytest.fixture
def pipeline(config):
    """Create test pipeline."""
    return NovaPipeline(config)

async def test_split_content_detection(pipeline, temp_workspace):
    """Test content section detection."""
    split_phase = SplitPhase(pipeline)
    
    # Process test file
    test_file = temp_workspace['input_dir'] / "20240119-test.parsed.md"
    await split_phase._process_file(test_file, temp_workspace['output_dir'])
    
    # Verify Summary.md was created and contains correct content
    summary_path = temp_workspace['output_dir'] / "Summary.md"
    assert summary_path.exists()
    summary_content = summary_path.read_text()
    assert "# Summary" in summary_content
    assert "This is a summary of the document" in summary_content
    
    # Verify Raw Notes.md was created and contains correct content
    raw_notes_path = temp_workspace['output_dir'] / "Raw Notes.md"
    assert raw_notes_path.exists()
    raw_notes_content = raw_notes_path.read_text()
    assert "# Raw Notes" in raw_notes_content
    assert "These are the raw notes" in raw_notes_content

async def test_reference_system(pipeline, temp_workspace):
    """Test reference system for links and attachments."""
    split_phase = SplitPhase(pipeline)
    
    # Process test file
    test_file = temp_workspace['input_dir'] / "20240119-test.parsed.md"
    metadata = await split_phase._process_file(test_file, temp_workspace['output_dir'])
    
    # Verify attachments were processed
    assert metadata is not None
    assert metadata.attachments is not None
    assert len(metadata.attachments) == 3  # test.jpg, another.jpg, test.docx
    
    # Verify attachment references in Summary.md
    summary_path = temp_workspace['output_dir'] / "Summary.md"
    summary_content = summary_path.read_text()
    assert "![Test Image]" in summary_content
    assert "[Test Doc]" in summary_content

async def test_file_organization(pipeline, temp_workspace):
    """Test file organization and directory structure."""
    split_phase = SplitPhase(pipeline)
    
    # Process test file
    test_file = temp_workspace['input_dir'] / "20240119-test.parsed.md"
    await split_phase._process_file(test_file, temp_workspace['output_dir'])
    
    # Verify output directory structure
    output_dir = temp_workspace['output_dir']
    assert (output_dir / "Summary.md").exists()
    assert (output_dir / "Raw Notes.md").exists()
    assert (output_dir / "Attachments.md").exists()
    assert (output_dir / "attachments").exists()
    
    # Verify attachments are organized by date and type
    attachments_dir = output_dir / "attachments" / "20240119"
    assert attachments_dir.exists()
    assert (attachments_dir / "jpg").exists()
    assert (attachments_dir / "doc").exists()
    
    # Verify actual files exist
    assert (attachments_dir / "jpg" / "test.jpg").exists()
    assert (attachments_dir / "jpg" / "another.jpg").exists()
    assert (attachments_dir / "doc" / "test.docx").exists()

async def test_metadata_handling(pipeline, temp_workspace):
    """Test metadata handling and storage."""
    split_phase = SplitPhase(pipeline)
    
    # Process test file
    test_file = temp_workspace['input_dir'] / "20240119-test.parsed.md"
    metadata = await split_phase._process_file(test_file, temp_workspace['output_dir'])
    
    # Verify metadata
    assert metadata is not None
    assert metadata.processed is True
    assert len(metadata.attachments) == 3
    
    # Verify attachment metadata
    for attachment in metadata.attachments:
        assert "url" in attachment
        assert "text" in attachment
        assert "type" in attachment
        assert "id" in attachment 