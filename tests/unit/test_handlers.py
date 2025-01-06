"""Tests for file handlers."""

# Standard library
import os
import shutil
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# External dependencies
import pytest
from PIL import Image
from reportlab.pdfgen import canvas
from docx import Document

# Internal imports
from nova.context_processor.config.settings import CacheConfig, OpenAIConfig
from nova.context_processor.handlers.document import DocumentHandler
from nova.context_processor.handlers.image import ImageHandler
from nova.context_processor.handlers.markdown import MarkdownHandler
from nova.context_processor.models.document import DocumentMetadata


@pytest.fixture
def config():
    """Create test configuration."""
    # Create temp directories
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create required directories
        input_dir = temp_path / "input"
        output_dir = temp_path / "output"
        processing_dir = temp_path / "processing"
        cache_dir = temp_path / "cache"

        for dir_path in [input_dir, output_dir, processing_dir, cache_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Create config object
        config = NovaConfig(
            base_dir=str(temp_path),
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            processing_dir=str(processing_dir),
            cache=CacheConfig(dir=str(cache_dir), enabled=True, ttl=3600),
        )

        yield config

        # Cleanup
        shutil.rmtree(temp_path)


@pytest.fixture
def metadata(config):
    """Create test metadata."""
    return DocumentMetadata.from_file(
        file_path=Path(config.input_dir) / "test.md",
        handler_name="test",
        handler_version="0.1.0",
    )


class TestMarkdownHandler:
    """Tests for MarkdownHandler."""

    def test_init(self, config):
        """Test handler initialization."""
        handler = MarkdownHandler(config)
        assert handler.name == "markdown"
        assert handler.version == "0.1.0"
        assert handler.file_types == ["md", "markdown"]

    def test_update_links(self, config):
        """Test link updating."""
        handler = MarkdownHandler(config)

        # Test basic link
        content = "Here is a [link](test.md)"
        updated = handler._update_links(content)
        assert updated == "Here is a [ATTACH:DOC:test]"

        # Test image link
        content = "Here is an ![image](test.png)"
        updated = handler._update_links(content)
        assert updated == "Here is an ![ATTACH:IMAGE:test]"

        # Test multiple links
        content = "Here is a [link](test.md) and an ![image](test.png)"
        updated = handler._update_links(content)
        assert updated == "Here is a [ATTACH:DOC:test] and an ![ATTACH:IMAGE:test]"

        # Test external link (should not be transformed)
        content = "Here is an [external link](https://example.com)"
        updated = handler._update_links(content)
        assert updated == "Here is an [external link](https://example.com)"

    @pytest.mark.asyncio
    async def test_process_markdown(self, config):
        """Test markdown processing."""
        handler = MarkdownHandler(config)

        # Create test file
        test_file = Path(config.input_dir) / "test.md"
        test_file.write_text("# Test\n\nThis is a test.")

        # Process file
        metadata = DocumentMetadata(title="test")
        output_path = Path(config.output_dir) / "test.md"
        result = await handler.process_impl(test_file, output_path, metadata)

        assert result is not None
        assert result.processed is True
        assert result.title == "test"
        assert len(result.output_files) == 1

        # Check output file
        output_file = list(result.output_files)[0]
        assert output_file.exists()
        content = output_file.read_text()
        assert "# Test" in content
        assert "This is a test." in content


class TestDocumentHandler:
    """Tests for DocumentHandler."""

    def test_init(self, config):
        """Test handler initialization."""
        handler = DocumentHandler(config)
        assert handler.name == "document"
        assert handler.version == "0.2.0"
        assert handler.file_types == ["pdf", "docx", "doc", "odt", "rtf"]

    @pytest.mark.asyncio
    async def test_process_pdf(self, config):
        """Test PDF processing."""
        handler = DocumentHandler(config)

        # Create test PDF file with actual content
        test_file = Path(config.input_dir) / "test.pdf"
        c = canvas.Canvas(str(test_file))
        c.drawString(100, 750, "Test PDF content")
        c.save()

        # Process file
        metadata = DocumentMetadata(title="test")
        output_path = Path(config.output_dir) / "test.md"
        result = await handler.process_impl(test_file, output_path, metadata)

        assert result is not None
        assert result.processed is True
        assert result.title == "test"
        assert len(result.output_files) == 1

        # Check output file
        output_file = list(result.output_files)[0]
        assert output_file.exists()
        content = output_file.read_text()
        assert "Test PDF content" in content

    @pytest.mark.asyncio
    async def test_process_docx(self, config):
        """Test DOCX processing."""
        handler = DocumentHandler(config)

        # Create test DOCX file with actual content
        test_file = Path(config.input_dir) / "test.docx"
        doc = Document()
        doc.add_paragraph("Test DOCX content")
        doc.save(test_file)

        # Process file
        metadata = DocumentMetadata(title="test")
        output_path = Path(config.output_dir) / "test.md"
        result = await handler.process_impl(test_file, output_path, metadata)

        assert result is not None
        assert result.processed is True
        assert result.title == "test"
        assert len(result.output_files) == 1

        # Check output file
        output_file = list(result.output_files)[0]
        assert output_file.exists()
        content = output_file.read_text()
        assert "Test DOCX content" in content


class TestImageHandler:
    """Tests for ImageHandler."""

    def test_init(self, config):
        """Test handler initialization."""
        # Set up mock APIs config with proper structure
        config.apis = None

        handler = ImageHandler(config)
        assert handler.name == "image"
        assert handler.version == "0.1.0"
        assert handler.file_types == ["jpg", "jpeg", "png", "heic", "svg"]
        assert handler.vision_client is None

    @pytest.mark.asyncio
    async def test_process_image(self, config, metadata):
        """Test image processing."""
        # Create test image file with actual content
        test_file = Path(config.input_dir) / "test.jpg"
        img = Image.new("RGB", (100, 100), color="red")
        img.save(test_file)

        # Configure OpenAI API key and mock client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test description"))]
        mock_client.chat.completions.create.return_value = mock_response

        # Set up config with proper OpenAI config structure
        nova.context_processor.config.settings APIConfig, OpenAIConfig

        config.apis = APIConfig(openai=OpenAIConfig(api_key="test_key"))

        handler = ImageHandler(config)
        handler.vision_client = mock_client
        output_path = Path(config.output_dir) / "test.md"
        result = await handler.process_impl(test_file, output_path, metadata)

        assert result is not None
        assert result.processed is True
        assert result.title == "test"
        assert len(result.output_files) == 1

        # Check output file
        output_file = list(result.output_files)[0]
        assert output_file.exists()
        content = output_file.read_text()
        assert "Test description" in content

    @pytest.mark.asyncio
    async def test_process_image_no_vision(self, config, metadata):
        """Test image processing without vision API."""
        # Create test image file with actual content
        test_file = Path(config.input_dir) / "test.jpg"
        img = Image.new("RGB", (100, 100), color="blue")
        img.save(test_file)

        # Set up config without OpenAI API key
        config.apis = None

        handler = ImageHandler(config)
        output_path = Path(config.output_dir) / "test.md"
        result = await handler.process_impl(test_file, output_path, metadata)

        assert result is not None
        assert result.processed is True
        assert result.title == "test"
        assert len(result.output_files) == 1

        # Check output file
        output_file = list(result.output_files)[0]
        assert output_file.exists()
        content = output_file.read_text()
        assert (
            "Failed to generate image description: OpenAI API not configured" in content
        )
