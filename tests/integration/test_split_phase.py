"""Integration tests for the split phase."""

import os
import pytest
from pathlib import Path
import shutil
from textwrap import dedent

from nova.phases.split import SplitPhase
from nova.config.manager import ConfigManager
from nova.core.pipeline import NovaPipeline


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
        },
        'apis': {
            'openai': {
                'api_key': "None"  # Explicitly disable OpenAI API for tests
            }
        }
    })
    
    # Create directories
    config.input_dir.mkdir(parents=True, exist_ok=True)
    config.processing_dir.mkdir(parents=True, exist_ok=True)
    config.cache_dir.mkdir(parents=True, exist_ok=True)
    
    return config


@pytest.fixture
def pipeline(test_config):
    """Create a test pipeline instance."""
    return NovaPipeline(test_config)


@pytest.fixture
def test_files(test_config):
    """Create test files for splitting."""
    # Create test files directory
    test_files_dir = test_config.processing_dir / "phases" / "parse"
    test_files_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a parsed markdown file
    md_file = test_files_dir / "test.parsed.md"
    md_file.write_text(dedent("""
        # Test Document
        
        This is a test document.
        
        ## RAW NOTES
        
        Some raw notes here.
        
        ## Attachments
        
        - [test.pdf](test.pdf)
        - [image.jpg](image.jpg)
    """).strip())
    
    return test_files_dir


@pytest.mark.asyncio
async def test_split_phase_basic(pipeline, test_config, test_files):
    """Test basic split functionality."""
    # Set up
    input_file = test_files / "test.parsed.md"
    split_dir = test_config.processing_dir / "phases" / "split"
    split_dir.mkdir(parents=True, exist_ok=True)
    
    # Create split phase with pipeline
    split_phase = pipeline.phases["split"]
    
    # Process file
    metadata = await split_phase.process(input_file, split_dir)
    
    # Verify
    assert split_dir.exists()
    assert metadata is not None
    assert metadata.processed
    assert len(metadata.output_files) > 0
    assert any(f.name.endswith(".md") for f in metadata.output_files)


@pytest.mark.asyncio
async def test_split_phase_with_attachments(pipeline, test_config, test_files):
    """Test splitting with attachments."""
    # Set up
    input_file = test_files / "test.parsed.md"
    split_dir = test_config.processing_dir / "phases" / "split"
    split_dir.mkdir(parents=True, exist_ok=True)
    
    # Add some attachments
    attachments_dir = test_files / "attachments"
    attachments_dir.mkdir(parents=True, exist_ok=True)
    (attachments_dir / "test.pdf").write_bytes(b"fake pdf")
    (attachments_dir / "image.jpg").write_bytes(b"fake image")
    
    # Create split phase with pipeline
    split_phase = pipeline.phases["split"]
    
    # Process file
    metadata = await split_phase.process(input_file, split_dir)
    
    # Verify
    assert split_dir.exists()
    assert metadata is not None
    assert metadata.processed
    assert len(metadata.output_files) > 0
    assert any(f.name.endswith(".md") for f in metadata.output_files)
    assert (split_dir / "attachments").exists()
    assert (split_dir / "attachments" / "test.pdf").exists()
    assert (split_dir / "attachments" / "image.jpg").exists()


@pytest.mark.asyncio
async def test_split_phase_multiple_files(pipeline, test_config, test_files):
    """Test splitting multiple files."""
    # Set up
    split_dir = test_config.processing_dir / "phases" / "split"
    split_dir.mkdir(parents=True, exist_ok=True)
    
    # Create multiple test files
    files = []
    for i in range(3):
        file = test_files / f"test{i}.parsed.md"
        file.write_text(dedent(f"""
            # Test Document {i}
            
            This is test document {i}.
            
            ## RAW NOTES
            
            Raw notes for document {i}.
        """).strip())
        files.append(file)
    
    # Create split phase with pipeline
    split_phase = pipeline.phases["split"]
    
    # Process files
    for file in files:
        metadata = await split_phase.process(file, split_dir)
        assert metadata is not None
        assert metadata.processed
    
    # Verify
    assert split_dir.exists()
    assert len(list(split_dir.glob("*.md"))) == len(files)


@pytest.mark.asyncio
async def test_split_phase_error_handling(pipeline, test_config, test_files):
    """Test error handling in split phase."""
    # Set up
    split_dir = test_config.processing_dir / "phases" / "split"
    split_dir.mkdir(parents=True, exist_ok=True)
    
    # Create an invalid parsed file
    bad_file = test_files / "bad.parsed.md"
    bad_file.write_text("Invalid markdown content")
    
    # Create split phase with pipeline
    split_phase = pipeline.phases["split"]
    
    # Process file
    metadata = await split_phase.process(bad_file, split_dir)
    
    # Verify
    assert split_dir.exists()
    assert metadata is None
    assert bad_file in pipeline.failed_files 