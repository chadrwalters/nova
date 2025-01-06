"""
Unit tests for Nova image handler.
"""
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from nova.context_processor.config.manager import ConfigManager
from nova.context_processor.config.settings import APIConfig, OpenAIConfig
from nova.context_processor.handlers.image import ImageHandler
from nova.context_processor.models.document import DocumentMetadata


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Test image description"))]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def test_config(mock_fs):
    """Create test configuration."""
    config = NovaConfig(
        base_dir=str(mock_fs["root"]),
        input_dir=str(mock_fs["input"]),
        output_dir=str(mock_fs["output"]),
        processing_dir=str(mock_fs["processing"]),
        cache=CacheConfig(dir=str(mock_fs["cache"]), enabled=True, ttl=3600),
        apis=APIConfig(
            openai=OpenAIConfig(api_key="test_key", model="gpt-4o", max_tokens=300)
        ),
    )
    return ConfigManager(config)


@pytest.fixture
def test_image():
    """Create a test image."""
    img = Image.new("RGB", (100, 100), color="red")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.read()


@pytest.mark.unit
@pytest.mark.handlers
@pytest.mark.asyncio
async def test_image_handler_mock_api(
    test_config, test_image, mock_openai_client, mock_fs
):
    """Test image handler with mocked OpenAI API."""
    handler = ImageHandler(test_config)
    handler.vision_client = mock_openai_client

    # Create test file path and metadata
    file_path = mock_fs["input"] / "test.png"
    output_path = mock_fs["output"] / "test.parsed.md"

    # Write test image to file
    file_path.write_bytes(test_image)

    metadata = DocumentMetadata.from_file(file_path, handler.name, handler.version)

    # Process image
    result = await handler.process_file_impl(file_path, output_path, metadata)

    # Verify results
    assert result is not None
    assert result.processed is True
    assert result.title == "test"
    assert mock_openai_client.chat.completions.create.called


@pytest.mark.unit
@pytest.mark.handlers
@pytest.mark.openai
def test_image_handler_real_api(test_config, test_image):
    """Test image handler with real OpenAI API."""
    pytest.skip("need --openai-api option to run")


@pytest.mark.unit
@pytest.mark.handlers
@pytest.mark.asyncio
async def test_image_handler_no_api(test_config, test_image, mock_fs):
    """Test image handler without OpenAI API."""
    # Remove API key
    test_config.config.apis.openai.api_key = None

    handler = ImageHandler(test_config)

    # Create test file path and metadata
    file_path = mock_fs["input"] / "test.png"
    output_path = mock_fs["output"] / "test.parsed.md"

    # Write test image to file
    file_path.write_bytes(test_image)

    metadata = DocumentMetadata.from_file(file_path, handler.name, handler.version)

    # Process image
    result = await handler.process_file_impl(file_path, output_path, metadata)

    # Verify results
    assert result is not None
    assert result.processed is True
    assert result.title == "test"
    assert "Failed to generate image description" in str(result.metadata)
