"""Integration tests for the Nova pipeline."""

import os
import pytest
from pathlib import Path
import shutil
from textwrap import dedent
import yaml

from nova.core.nova import Nova
from nova.config.manager import ConfigManager
from nova.handlers.registry import HandlerRegistry


@pytest.fixture
def test_config(tmp_path):
    """Create a test configuration with temporary directories."""
    config = ConfigManager()
    
    # Set up temporary directories using update_config
    config.update_config({
        'base_dir': str(tmp_path),
        'input_dir': str(tmp_path / "_NovaInput"),  # Use _NovaInput to match production
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
    
    # Write config to file
    config_path = tmp_path / "nova.test.yaml"
    config_dict = config.config.dict()
    # Convert Path objects to strings
    config_dict['base_dir'] = str(config_dict['base_dir'])
    config_dict['input_dir'] = str(config_dict['input_dir'])
    config_dict['output_dir'] = str(config_dict['output_dir'])
    config_dict['processing_dir'] = str(config_dict['processing_dir'])
    config_dict['cache']['dir'] = str(config_dict['cache']['dir'])
    with open(config_path, 'w') as f:
        yaml.dump(config_dict, f)
    
    # Ensure no OpenAI API key in environment
    if 'OPENAI_API_KEY' in os.environ:
        del os.environ['OPENAI_API_KEY']
    
    return config


@pytest.fixture
def test_files(test_config):
    """Create test files in a realistic directory structure."""
    from PIL import Image
    import numpy as np
    from PyPDF2 import PdfWriter
    import io
    
    # Create test directories
    input_dir = test_config.input_dir
    categories = ["Documents", "Images", "Notes"]
    for category in categories:
        (input_dir / category).mkdir(parents=True, exist_ok=True)
    
    # Create test files in Documents
    docs_dir = input_dir / "Documents"
    
    # Create PDFs
    for pdf_name in ["report.pdf", "notes.pdf"]:
        writer = PdfWriter()
        page = writer.add_blank_page(width=612, height=792)
        pdf_bytes = io.BytesIO()
        writer.write(pdf_bytes)
        pdf_content = pdf_bytes.getvalue()
        (docs_dir / pdf_name).write_bytes(pdf_content)
    
    # Create text files
    (docs_dir / "meeting_notes.txt").write_text("Meeting notes content")
    (docs_dir / "todo.txt").write_text("Todo list content")
    
    # Create test files in Images
    images_dir = input_dir / "Images"
    for filename in ["screenshot.png", "photo.jpg"]:
        img = Image.fromarray(np.zeros((32, 32, 3), dtype=np.uint8))
        img.save(images_dir / filename)
    
    # Create a dummy HEIC file
    (images_dir / "photo.heic").write_bytes(b"HEIC")
    
    # Create test files in Notes with subdirectories
    notes_dir = input_dir / "Notes"
    (notes_dir / "Work").mkdir(parents=True, exist_ok=True)
    (notes_dir / "Personal").mkdir(parents=True, exist_ok=True)
    
    (notes_dir / "Work" / "project.md").write_text("Project notes")
    (notes_dir / "Personal" / "diary.md").write_text("Diary entry")
    
    return input_dir


@pytest.mark.asyncio
async def test_input_file_discovery(test_config, test_files):
    """Test that the pipeline correctly discovers and processes files in _NovaInput."""
    # Create Nova pipeline with test config
    config_path = test_config.base_dir / "nova.test.yaml"
    nova = Nova(config_path=config_path)
    
    # Process all files in input directory
    await nova.process_directory()
    
    # Check that all files were discovered and processed
    parse_dir = test_config.processing_dir / "phases" / "parse"
    
    # Check Documents
    assert (parse_dir / "Documents" / "report.parsed.md").exists()
    assert (parse_dir / "Documents" / "notes.parsed.md").exists()
    assert (parse_dir / "Documents" / "meeting_notes.parsed.md").exists()
    assert (parse_dir / "Documents" / "todo.parsed.md").exists()
    
    # Check Images
    assert (parse_dir / "Images" / "screenshot.parsed.md").exists()
    assert (parse_dir / "Images" / "photo.parsed.md").exists()
    assert (parse_dir / "Images" / "photo.parsed.md").exists()  # HEIC gets converted to jpg
    
    # Check Notes and subdirectories
    assert (parse_dir / "Notes" / "Work" / "project.parsed.md").exists()
    assert (parse_dir / "Notes" / "Personal" / "diary.parsed.md").exists()
    
    # Verify file type detection through handler selection
    # Read a few key files and check their content
    
    # Check PDF handling
    report_content = (parse_dir / "Documents" / "report.parsed.md").read_text()
    assert "# report" in report_content
    assert "[Original File: report.pdf]" in report_content
    
    # Check text handling
    notes_content = (parse_dir / "Documents" / "meeting_notes.parsed.md").read_text()
    assert "# meeting_notes" in notes_content
    assert "Meeting notes content" in notes_content
    
    # Check image handling
    screenshot_content = (parse_dir / "Images" / "screenshot.parsed.md").read_text()
    assert "# screenshot" in screenshot_content
    assert "32x32" in screenshot_content  # Image dimensions
    
    # Check markdown handling
    project_content = (parse_dir / "Notes" / "Work" / "project.parsed.md").read_text()
    assert "# project" in project_content
    assert "Project notes" in project_content 