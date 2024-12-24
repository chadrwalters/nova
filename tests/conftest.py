import pytest
from pathlib import Path

@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for tests."""
    return tmp_path

@pytest.fixture
def test_data_dir():
    """Return the path to the test data directory."""
    return Path(__file__).parent / 'data'

@pytest.fixture
def test_output_dir(temp_dir):
    """Create and return a temporary output directory."""
    output_dir = temp_dir / 'output'
    output_dir.mkdir(exist_ok=True)
    return output_dir

@pytest.fixture
def test_input_dir(temp_dir):
    """Create and return a temporary input directory."""
    input_dir = temp_dir / 'input'
    input_dir.mkdir(exist_ok=True)
    return input_dir

@pytest.fixture
def test_processing_dir(temp_dir):
    """Create and return a temporary processing directory."""
    processing_dir = temp_dir / 'processing'
    processing_dir.mkdir(exist_ok=True)
    return processing_dir 