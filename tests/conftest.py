import os
import pytest
from pathlib import Path

@pytest.fixture
def test_data_dir() -> Path:
    """Return the path to the test data directory."""
    return Path(__file__).parent / "fixtures"

@pytest.fixture
def sample_markdown_file(test_data_dir) -> Path:
    """Create a sample markdown file for testing."""
    file_path = test_data_dir / "sample.md"
    content = """# Test Document
    
## Section 1
This is a test document.

## Section 2
With multiple sections.
"""
    file_path.write_text(content)
    yield file_path
    if file_path.exists():
        file_path.unlink()

@pytest.fixture
def sample_image_file(test_data_dir) -> Path:
    """Create a sample image file for testing."""
    from PIL import Image
    file_path = test_data_dir / "sample.png"
    img = Image.new('RGB', (100, 100), color='red')
    img.save(file_path)
    yield file_path
    if file_path.exists():
        file_path.unlink()

@pytest.fixture
def temp_output_dir(tmp_path) -> Path:
    """Create a temporary directory for test outputs."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir 