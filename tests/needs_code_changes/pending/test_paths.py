"""Tests for the paths module."""

import os
from pathlib import Path
import pytest
from nova.core.paths import NovaPaths

@pytest.fixture(autouse=True)
def clean_env():
    """Clean environment variables before each test."""
    # Save original environment
    original_env = {
        'NOVA_BASE_DIR': os.environ.get('NOVA_BASE_DIR'),
        'NOVA_INPUT_DIR': os.environ.get('NOVA_INPUT_DIR'),
        'NOVA_OUTPUT_DIR': os.environ.get('NOVA_OUTPUT_DIR'),
        'NOVA_PROCESSING_DIR': os.environ.get('NOVA_PROCESSING_DIR'),
        'NOVA_TEMP_DIR': os.environ.get('NOVA_TEMP_DIR')
    }
    
    # Clear environment variables
    for key in original_env:
        if key in os.environ:
            del os.environ[key]
    
    yield
    
    # Restore original environment
    for key, value in original_env.items():
        if value is not None:
            os.environ[key] = value
        elif key in os.environ:
            del os.environ[key]

def test_nova_paths_from_env():
    """Test NovaPaths creation from environment variables."""
    # Set test environment variables
    os.environ['NOVA_BASE_DIR'] = '/test/base'
    os.environ['NOVA_PROCESSING_DIR'] = '/test/base/_NovaProcessing'
    
    paths = NovaPaths.from_env()
    
    # Test base directories
    assert paths.base_dir == Path('/test/base')
    assert paths.input_dir == Path('/test/base/_NovaInput')
    assert paths.output_dir == Path('/test/base/_NovaOutput')
    assert paths.processing_dir == Path('/test/base/_NovaProcessing')
    assert paths.temp_dir == Path('/test/base/_NovaProcessing/temp')
    assert paths.state_dir == Path('/test/base/_NovaProcessing/.state')
    
    # Test phase directories
    assert paths.phase_dirs['markdown_parse'] == Path('/test/base/_NovaProcessing/phases/markdown_parse')
    assert paths.phase_dirs['markdown_consolidate'] == Path('/test/base/_NovaProcessing/phases/markdown_consolidate')
    
    # Test image directories
    assert paths.image_dirs['original'] == Path('/test/base/_NovaProcessing/images/original')
    assert paths.image_dirs['processed'] == Path('/test/base/_NovaProcessing/images/processed')
    assert paths.image_dirs['metadata'] == Path('/test/base/_NovaProcessing/images/metadata')
    assert paths.image_dirs['cache'] == Path('/test/base/_NovaProcessing/images/cache')
    
    # Test office directories
    assert paths.office_dirs['assets'] == Path('/test/base/_NovaProcessing/office/assets')
    assert paths.office_dirs['temp'] == Path('/test/base/_NovaProcessing/office/temp')

def test_nova_paths_create_directories(tmp_path):
    """Test directory creation."""
    base_dir = tmp_path / 'nova'
    os.environ['NOVA_BASE_DIR'] = str(base_dir)
    os.environ['NOVA_PROCESSING_DIR'] = str(base_dir / '_NovaProcessing')
    
    paths = NovaPaths.from_env()
    paths.create_directories()
    
    # Verify base directories exist
    assert paths.base_dir.exists()
    assert paths.input_dir.exists()
    assert paths.output_dir.exists()
    assert paths.processing_dir.exists()
    assert paths.temp_dir.exists()
    assert paths.state_dir.exists()
    
    # Verify phase directories exist
    for dir_path in paths.phase_dirs.values():
        assert dir_path.exists()
    
    # Verify image directories exist
    for dir_path in paths.image_dirs.values():
        assert dir_path.exists()
    
    # Verify office directories exist
    for dir_path in paths.office_dirs.values():
        assert dir_path.exists()

def test_nova_paths_get_relative_path():
    """Test getting relative paths."""
    os.environ['NOVA_BASE_DIR'] = '/test/base'
    paths = NovaPaths.from_env()
    
    # Test relative path inside base directory
    path = Path('/test/base/some/file.txt')
    relative = paths.get_relative_path(path)
    assert relative == Path('some/file.txt')
    
    # Test path outside base directory
    path = Path('/other/path/file.txt')
    relative = paths.get_relative_path(path)
    assert relative == path  # Should return original path if not under base_dir