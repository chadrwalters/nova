"""Integration tests for the parse phase."""

import os
import pytest
from pathlib import Path
import shutil
from textwrap import dedent

from nova.phases.parse import ParsePhase
from nova.config.manager import ConfigManager
from nova.handlers.registry import HandlerRegistry
from nova.core.pipeline import NovaPipeline


@pytest.fixture
def test_config(tmp_path):
    """Create a test configuration with temporary directories."""
    from nova.config.manager import ConfigManager
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
    
    # Ensure no OpenAI API key in environment
    if 'OPENAI_API_KEY' in os.environ:
        del os.environ['OPENAI_API_KEY']
    
    return config


@pytest.fixture
def pipeline(test_config):
    """Create a test pipeline instance."""
    return NovaPipeline(test_config)


@pytest.fixture
def test_files(test_config):
    """Create test files for parsing."""
    # Create test files directory
    test_files_dir = test_config.input_dir / "test_files"
    test_files_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a simple text file
    text_file = test_files_dir / "text_test.txt"
    text_file.write_text("This is a test file.")
    
    # Create a markdown file
    md_file = test_files_dir / "md_test.md"
    md_file.write_text("# Test Markdown\nThis is a test markdown file.")
    
    return test_files_dir


@pytest.mark.asyncio
async def test_parse_phase_basic_text(pipeline, test_config, test_files):
    """Test basic text file parsing."""
    # Set up
    input_file = test_files / "text_test.txt"
    output_dir = test_config.processing_dir / "phases" / "parse"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create parse phase with pipeline
    parse_phase = pipeline.phases["parse"]
    
    # Process file
    metadata = await parse_phase.process(input_file, output_dir)
    
    # Verify
    assert metadata is not None
    assert metadata.processed
    assert len(metadata.output_files) > 0
    assert any(f.name.endswith(".parsed.md") for f in metadata.output_files)


@pytest.mark.asyncio
async def test_parse_phase_markdown_conversion(pipeline, test_config, test_files):
    """Test markdown file conversion."""
    # Set up
    input_file = test_files / "md_test.md"
    output_dir = test_config.processing_dir / "phases" / "parse"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create parse phase with pipeline
    parse_phase = pipeline.phases["parse"]
    
    # Process file
    metadata = await parse_phase.process(input_file, output_dir)
    
    # Verify
    assert metadata is not None
    assert metadata.processed
    assert len(metadata.output_files) > 0
    assert any(f.name.endswith(".parsed.md") for f in metadata.output_files)


@pytest.mark.asyncio
async def test_parse_phase_metadata(pipeline, test_config, test_files):
    """Test metadata extraction."""
    # Set up
    input_file = test_files / "md_test.md"
    output_dir = test_config.processing_dir / "phases" / "parse"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create parse phase with pipeline
    parse_phase = pipeline.phases["parse"]
    
    # Process file
    metadata = await parse_phase.process(input_file, output_dir)
    
    # Verify
    assert metadata is not None
    assert metadata.processed
    assert metadata.title == "md_test"


@pytest.mark.asyncio
async def test_parse_phase_error_handling(pipeline, test_config, test_files):
    """Test error handling."""
    # Set up
    input_file = test_files / "nonexistent.txt"
    output_dir = test_config.processing_dir / "phases" / "parse"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create parse phase with pipeline
    parse_phase = pipeline.phases["parse"]
    
    # Process file
    metadata = await parse_phase.process(input_file, output_dir)
    
    # Verify
    assert metadata is None  # No handler found for nonexistent file
    assert input_file in pipeline.failed_files
    
    # Test with existing but invalid file (binary data)
    invalid_file = test_files / "invalid.txt"
    invalid_file.write_bytes(b'\x80\x81\x82\x83')  # Invalid UTF-8 bytes
    
    # Process invalid file
    metadata = await parse_phase.process(invalid_file, output_dir)
    
    # Verify
    assert metadata is not None
    assert not metadata.processed
    assert metadata.error
    assert invalid_file in pipeline.failed_files


@pytest.mark.asyncio
async def test_parse_phase_image_handling(pipeline, test_config, test_files):
    """Test image file handling."""
    # Set up
    input_file = test_files / "test_image.jpg"
    input_file.write_bytes(b"fake image data")  # Create a fake image file
    output_dir = test_config.processing_dir / "phases" / "parse"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create parse phase with pipeline
    parse_phase = pipeline.phases["parse"]
    
    # Process file
    metadata = await parse_phase.process(input_file, output_dir)
    
    # Verify
    assert metadata is not None
    assert metadata.processed
    assert len(metadata.output_files) > 0
    assert any(f.name.endswith(".parsed.md") for f in metadata.output_files)


@pytest.mark.asyncio
async def test_image_handler_no_openai(pipeline, test_config, test_files):
    """Test image handling without OpenAI API key."""
    # Set up
    input_file = test_files / "test_image.jpg"
    input_file.write_bytes(b"fake image data")  # Create a fake image file
    output_dir = test_config.processing_dir / "phases" / "parse"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create parse phase with pipeline
    parse_phase = pipeline.phases["parse"]
    
    # Process file
    metadata = await parse_phase.process(input_file, output_dir)
    
    # Verify
    assert metadata is not None
    assert metadata.processed
    assert len(metadata.output_files) > 0
    assert any(f.name.endswith(".parsed.md") for f in metadata.output_files) 