"""Integration tests for the parse phase."""

import os
import pytest
from pathlib import Path
import shutil
from textwrap import dedent

from nova.phases.parse import ParsePhase
from nova.config.manager import ConfigManager
from nova.handlers.registry import HandlerRegistry


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
def test_files(test_config):
    """Create test files for testing."""
    from PIL import Image
    import numpy as np
    from PyPDF2 import PdfWriter
    import io
    
    # Create test directory
    input_dir = test_config.input_dir / "test_files"
    input_dir.mkdir(parents=True, exist_ok=True)
    
    # Create test text file
    (input_dir / "text_test.txt").write_text("Test content")
    
    # Create test PDF files using PyPDF2
    for pdf_name in ["pdf_test.pdf", "pdf_test2.pdf"]:
        writer = PdfWriter()
        page = writer.add_blank_page(width=612, height=792)  # Standard letter size
        pdf_bytes = io.BytesIO()
        writer.write(pdf_bytes)
        pdf_content = pdf_bytes.getvalue()
        (input_dir / pdf_name).write_bytes(pdf_content)
    
    # Create test image files
    for filename in ["png_test.png", "jpg_test.jpg"]:
        # Create a small test image
        img = Image.fromarray(np.zeros((32, 32, 3), dtype=np.uint8))
        img.save(input_dir / filename)
    
    # Create a dummy HEIC file (since we can't easily create a real one)
    (input_dir / "heic_test.heic").write_bytes(b"HEIC")
    
    return input_dir


@pytest.mark.asyncio
async def test_parse_phase_basic_text(test_config, test_files):
    """Test basic text file processing."""
    # Create parse phase
    handler_registry = HandlerRegistry(test_config)
    parse_phase = ParsePhase(test_config, handler_registry)
    output_dir = test_config.processing_dir / "phases" / "parse"
    
    # Process file
    input_file = test_files / "text_test.txt"
    metadata = await parse_phase.process(input_file, output_dir)
    
    # Check that file was processed
    assert metadata is not None
    assert metadata.processed
    
    # Check output file
    parsed_file = output_dir / "test_files" / "text_test.parsed.md"
    assert parsed_file.exists()
    
    # Check content
    content = parsed_file.read_text(encoding='utf-8')
    assert "# text_test" in content
    assert "Test content" in content
    assert "[Download Original]" in content
    assert "## Content" in content


@pytest.mark.asyncio
async def test_parse_phase_markdown_conversion(test_config, test_files):
    """Test markdown conversion of PDF files."""
    # Create parse phase
    handler_registry = HandlerRegistry(test_config)
    parse_phase = ParsePhase(test_config, handler_registry)
    output_dir = test_config.processing_dir / "phases" / "parse"
    
    # Process file
    input_file = test_files / "pdf_test2.pdf"
    metadata = await parse_phase.process(input_file, output_dir)
    
    # Check that file was processed
    assert metadata is not None
    assert metadata.processed
    
    # Check output file
    parsed_file = output_dir / "test_files" / "pdf_test2.parsed.md"
    assert parsed_file.exists()
    
    # Check content
    content = parsed_file.read_text(encoding='utf-8')
    assert "# pdf_test2" in content
    assert "[Original File: pdf_test2.pdf]" in content  # Should have link to original
    assert "pdf_test2.pdf" in content  # Should reference the PDF file
    assert "## Content" in content  # Should have content section
    assert not metadata.has_errors  # Should not have errors since PDF is valid


@pytest.mark.asyncio
async def test_parse_phase_metadata(test_config, test_files):
    """Test metadata handling during parsing."""
    # Get test file
    test_file = test_files / "pdf_test2.pdf"
    
    # Create parse phase
    handler_registry = HandlerRegistry(test_config)
    parse_phase = ParsePhase(test_config, handler_registry)
    
    # Process file
    output_dir = test_config.processing_dir / "phases" / "parse"
    metadata = await parse_phase.process(test_file, output_dir)
    
    # Check metadata
    assert metadata is not None
    assert str(metadata.file_path) == str(test_file)  # Convert both to string for comparison
    assert metadata.processed
    assert metadata.handler_name == "document"  # Should be handled by document handler
    assert not metadata.has_errors  # Should be no errors
    assert 'output_files' in metadata.metadata  # Should have output files in metadata


@pytest.mark.asyncio
async def test_parse_phase_error_handling(test_config, test_files):
    """Test error handling during parsing."""
    # Create an unreadable file
    bad_file = test_files / "bad_file.txt"
    bad_file.write_text("Some content", encoding='utf-8')
    bad_file.chmod(0o000)  # Make file unreadable
    
    # Create parse phase
    handler_registry = HandlerRegistry(test_config)
    parse_phase = ParsePhase(test_config, handler_registry)
    
    # Process file
    output_dir = test_config.processing_dir / "phases" / "parse"
    metadata = await parse_phase.process(bad_file, output_dir)
    
    # Check metadata
    assert metadata is not None  # Handler returns metadata with error
    assert metadata.has_errors  # Should have errors
    
    # Clean up
    bad_file.chmod(0o644)  # Make file readable again for cleanup
    bad_file.unlink()


@pytest.mark.asyncio
async def test_parse_phase_image_handling(test_config, test_files):
    """Test handling of image files without OpenAI API."""
    # Test image files with their expected section headers
    test_cases = [
        ("png_test.png", "## Content Analysis"),  # Small image = diagram
        ("jpg_test.jpg", "## Content Analysis"),  # Small image = diagram
    ]
    
    # Create parse phase
    handler_registry = HandlerRegistry(test_config)
    parse_phase = ParsePhase(test_config, handler_registry)
    output_dir = test_config.processing_dir / "phases" / "parse"
    
    # Process each image
    for filename, expected_header in test_cases:
        input_file = test_files / filename
        
        # Process file
        metadata = await parse_phase.process(input_file, output_dir)
        
        # Check that file was processed
        assert metadata is not None
        assert metadata.processed
        
        # Check output file
        parsed_file = output_dir / "test_files" / f"{filename.rsplit('.', 1)[0]}.parsed.md"
        assert parsed_file.exists()
        
        # Check content
        content = parsed_file.read_text(encoding='utf-8')
        assert expected_header in content  # Check for the expected section header
        
        # Check image reference
        assert f"![{filename.rsplit('.', 1)[0]}]" in content
            
        # Verify basic image info is included
        assert "Image:" in content
        assert "32x32" in content  # We know the test image size
        assert "RGB" in content  # We know the test image mode


@pytest.mark.asyncio
async def test_image_handler_no_openai(test_config, test_files):
    """Test that image handler works without OpenAI API and doesn't make API calls."""
    from nova.handlers.image import ImageHandler
    
    # Create image handler
    handler = ImageHandler(test_config)
    
    # Verify OpenAI client is not initialized
    assert handler.openai_client is None
    
    # Process a test image
    test_image = test_files / "jpg_test.jpg"
    output_dir = test_config.processing_dir / "test_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process image
    metadata = await handler.process(test_image, output_dir, None)
    
    # Verify processing succeeded without API
    assert metadata is not None
    assert metadata.processed
    assert not metadata.has_errors
    
    # Check output file
    output_file = output_dir / f"{test_image.stem}.parsed.md"
    assert output_file.exists()
    
    # Verify content has basic image info but no API-generated content
    content = output_file.read_text(encoding='utf-8')
    assert "Image:" in content
    assert "32x32" in content  # We know the test image size
    assert "RGB" in content  # We know the test image mode
    assert "JPEG" in content.upper()  # We know the test image format
    assert "No context available" not in content  # Should get basic info, not error 