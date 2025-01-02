"""Unit tests for the BaseHandler class."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from nova.config.manager import ConfigManager
from nova.config.settings import NovaConfig, CacheConfig
from nova.handlers.base import BaseHandler, ProcessingStatus, ProcessingResult
from nova.models.document import DocumentMetadata
from nova.cache.manager import CacheManager
from nova.utils.output_manager import OutputManager


class TestHandler(BaseHandler):
    """Test handler implementation."""
    
    name = "test"
    version = "0.1.0"
    file_types = ["test"]
    
    async def process_impl(self, file_path: Path, metadata: DocumentMetadata) -> DocumentMetadata:
        """Test implementation."""
        return metadata


@pytest.fixture
def config(tmp_path):
    """Create test config."""
    config = Mock(spec=ConfigManager)
    
    # Set up required paths
    base_dir = tmp_path / "nova"
    input_dir = base_dir / "input"
    output_dir = base_dir / "output"
    processing_dir = base_dir / "processing"
    cache_dir = base_dir / "cache"
    
    # Create directories
    for dir_path in [input_dir, output_dir, processing_dir, cache_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    # Mock config properties
    config.base_dir = base_dir
    config.input_dir = input_dir
    config.output_dir = output_dir
    config.processing_dir = processing_dir
    config.cache_dir = cache_dir
    
    # Mock NovaConfig
    nova_config = Mock(spec=NovaConfig)
    nova_config.base_dir = base_dir
    nova_config.input_dir = input_dir
    nova_config.output_dir = output_dir
    nova_config.processing_dir = processing_dir
    
    # Mock CacheConfig
    cache_config = Mock(spec=CacheConfig)
    cache_config.dir = cache_dir
    cache_config.enabled = True
    cache_config.ttl = 3600
    
    nova_config.cache = cache_config
    config.config = nova_config
    config.cache = cache_config
    
    return config


@pytest.fixture
def handler(config, monkeypatch):
    """Create test handler with mocked dependencies."""
    # Mock CacheManager
    mock_cache_manager = Mock(spec=CacheManager)
    mock_cache_manager.cache_dir = config.cache_dir
    monkeypatch.setattr("nova.handlers.base.CacheManager", lambda x: mock_cache_manager)
    
    # Mock OutputManager
    mock_output_manager = Mock(spec=OutputManager)
    mock_output_manager.get_output_path_for_phase.return_value = config.output_dir / "test.md"
    monkeypatch.setattr("nova.handlers.base.OutputManager", lambda x: mock_output_manager)
    
    return TestHandler(config)


def test_handler_initialization(handler):
    """Test handler initialization."""
    assert handler.name == "test"
    assert handler.version == "0.1.0"
    assert handler.file_types == ["test"]
    assert handler._processing_status == ProcessingStatus.NOT_STARTED
    assert handler.markdown_writer is not None


@pytest.mark.asyncio
async def test_write_markdown(handler, tmp_path):
    """Test markdown writing with templates."""
    # Create test files
    file_path = tmp_path / "test.txt"
    file_path.write_text("test content")
    output_path = tmp_path / "test.md"
    
    # Test basic markdown writing
    result = handler._write_markdown(
        markdown_path=output_path,
        title="Test Title",
        file_path=file_path,
        content="Test Content",
        metadata={"key": "value"}
    )
    
    assert result is True
    assert output_path.exists()
    content = output_path.read_text()
    
    # Check content structure
    assert "# Test Title" in content
    assert "Test Content" in content
    assert "key: value" in content
    assert "test.txt" in content


@pytest.mark.asyncio
async def test_process_file(handler, tmp_path):
    """Test file processing."""
    # Create test file
    file_path = tmp_path / "test.test"
    file_path.write_text("test content")
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    # Process file
    result = await handler.process(file_path, output_dir)
    
    assert result.status == ProcessingStatus.COMPLETED
    assert result.metadata is not None
    assert result.error is None


@pytest.mark.asyncio
async def test_process_unsupported_file(handler, tmp_path):
    """Test processing unsupported file type."""
    # Create test file with unsupported extension
    file_path = tmp_path / "test.unsupported"
    file_path.write_text("test content")
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    # Process file
    result = await handler.process(file_path, output_dir)
    
    assert result.status == ProcessingStatus.SKIPPED
    assert result.metadata is None
    assert "Unsupported file type" in result.error


@pytest.mark.asyncio
async def test_process_nonexistent_file(handler, tmp_path):
    """Test processing nonexistent file."""
    file_path = tmp_path / "nonexistent.test"
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    # Process file
    result = await handler.process(file_path, output_dir)
    
    assert result.status == ProcessingStatus.SKIPPED
    assert result.metadata is None
    assert "does not exist" in result.error


@pytest.mark.asyncio
async def test_process_with_metadata(handler, tmp_path):
    """Test processing with existing metadata."""
    # Create test file
    file_path = tmp_path / "test.test"
    file_path.write_text("test content")
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    # Create metadata
    metadata = DocumentMetadata.from_file(file_path, handler.name, handler.version)
    metadata.title = "Test Title"
    
    # Process file
    result = await handler.process(file_path, output_dir, metadata)
    
    assert result.status == ProcessingStatus.COMPLETED
    assert result.metadata is not None
    assert result.metadata.title == "Test Title"
    assert result.error is None 