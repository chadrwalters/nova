"""Tests for file handlers."""

import os
import pytest
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
from reportlab.pdfgen import canvas
from io import BytesIO

from nova.models.document import DocumentMetadata
from nova.config.settings import NovaConfig, CacheConfig
from nova.handlers.markdown import MarkdownHandler
from nova.handlers.document import DocumentHandler
from nova.handlers.image import ImageHandler


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
            cache=CacheConfig(
                dir=str(cache_dir),
                enabled=True,
                ttl=3600
            )
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
        handler_version="0.1.0"
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
        content = """
        # Test Document
        
        [Link 1](file1.pdf)
        [Link 2](file2.docx)
        ![Image](image.jpg)
        [External](https://example.com)
        """
        
        updated = handler._update_links(content)
        assert "[ATTACH:PDF:file1]" in updated
        assert "[ATTACH:DOC:file2]" in updated
        assert "![ATTACH:IMAGE:image]" in updated
        assert "[External](https://example.com)" in updated
        
    async def test_process_markdown(self, config, metadata):
        """Test markdown processing."""
        # Create test file
        test_file = Path(config.input_dir) / "test.md"
        test_content = """
        # Test Document
        
        This is a test markdown file.
        [Link](file.pdf)
        """
        test_file.write_text(test_content)
        
        handler = MarkdownHandler(config)
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
        assert "# Test Document" in content
        assert "[ATTACH:PDF:file]" in content


class TestDocumentHandler:
    """Tests for DocumentHandler."""
    
    def test_init(self, config):
        """Test handler initialization."""
        handler = DocumentHandler(config)
        assert handler.name == "document"
        assert handler.version == "0.2.0"
        assert handler.file_types == ["pdf", "docx", "doc", "odt", "rtf"]
        
    @patch('pypdf.PdfReader')
    async def test_process_pdf(self, mock_pdf_reader, config, metadata):
        """Test PDF processing."""
        # Mock PDF reader
        mock_reader = Mock()
        mock_reader.pages = [Mock(extract_text=lambda: "Test content")]
        mock_reader.metadata = {"Title": "Test PDF"}
        mock_pdf_reader.return_value = mock_reader
        
        # Create test file with actual content
        test_file = Path(config.input_dir) / "test.pdf"
        buffer = BytesIO()
        c = canvas.Canvas(buffer)
        c.drawString(100, 100, "Test content")
        c.save()
        test_file.write_bytes(buffer.getvalue())
        
        handler = DocumentHandler(config)
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
        assert "Test content" in content
        
    @patch('nova.handlers.document.DocxDocument')
    async def test_process_docx(self, mock_docx, config, metadata):
        """Test DOCX processing."""
        # Mock Document
        mock_doc = Mock()
        mock_doc.paragraphs = [Mock(text="Test content")]
        mock_docx.return_value = mock_doc

        # Create test file
        test_file = Path(config.input_dir) / "test.docx"
        test_file.touch()

        # Mock the Document class to return our mock doc
        mock_docx.side_effect = lambda file_path: mock_doc

        handler = DocumentHandler(config)
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
        assert "Test content" in content


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
        
    async def test_process_image(self, config, metadata):
        """Test image processing."""
        # Create test image file with actual content
        test_file = Path(config.input_dir) / "test.jpg"
        img = Image.new('RGB', (100, 100), color='red')
        img.save(test_file)
        
        # Configure OpenAI API key and mock client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test description"))]
        mock_client.chat.completions.create.return_value = mock_response
        
        # Set up config with proper OpenAI config structure
        from nova.config.settings import APIConfig, OpenAIConfig
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
        
    async def test_process_image_no_vision(self, config, metadata):
        """Test image processing without vision API."""
        # Create test image file with actual content
        test_file = Path(config.input_dir) / "test.jpg"
        img = Image.new('RGB', (100, 100), color='blue')
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
        assert "Failed to generate image description - no vision API configured" in content 