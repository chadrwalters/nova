"""Unit tests for Nova file handlers."""
import pytest
from pathlib import Path
import re
from nova.handlers.markdown import MarkdownHandler
from nova.core.metadata import FileMetadata
from nova.handlers.document import DocumentHandler
from nova.handlers.image import ImageHandler
import os

class TestMarkdownHandlerBasic:
    """Tests for the MarkdownHandler basic functionality."""
    
    @pytest.fixture
    async def markdown_handler(self, mock_config):
        """Create a MarkdownHandler instance for testing."""
        return MarkdownHandler(mock_config)
    
    @pytest.mark.requires_state
    async def test_update_links(self, markdown_handler, test_data_dir):
        """Test updating links in markdown content."""
        # Set up test file
        test_file = test_data_dir / "input" / "markdown" / "simple.md"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        with open(test_file, "w") as f:
            f.write("# Test\n\nLink to [image](test.jpg)")

        # Create metadata
        file_metadata = FileMetadata(file_path=test_file)
        file_metadata.add_output_file(test_data_dir / "output" / "test.parsed.md")

        # Process file
        await markdown_handler.process(test_file, file_metadata)

        # Verify link updates
        assert file_metadata.processed
        assert not file_metadata.has_errors
        assert len(file_metadata.links) > 0
    
    @pytest.mark.requires_state
    async def test_parsed_md_output(self, markdown_handler, test_data_dir):
        """Test parsing markdown file with images."""
        # Set up test file
        test_file = test_data_dir / "input" / "markdown" / "with_images.md"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        with open(test_file, "w") as f:
            f.write("# Test\n\n![Image](test.jpg)")

        # Create metadata
        file_metadata = FileMetadata(file_path=test_file)
        file_metadata.add_output_file(test_data_dir / "output" / "test.parsed.md")

        # Process file
        await markdown_handler.process(test_file, file_metadata)

        # Verify output
        assert file_metadata.processed
        assert not file_metadata.has_errors
        assert len(file_metadata.output_files) > 0
    
    @pytest.mark.requires_state
    async def test_metadata_update(self, markdown_handler, test_data_dir):
        """Test metadata updates during markdown processing."""
        # Set up test file
        test_file = test_data_dir / "input" / "markdown" / "simple.md"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        with open(test_file, "w") as f:
            f.write("# Test\n\nSome content")

        # Create metadata
        file_metadata = FileMetadata(file_path=test_file)
        file_metadata.add_output_file(test_data_dir / "output" / "test.parsed.md")

        # Process file
        await markdown_handler.process(test_file, file_metadata)

        # Verify metadata updates
        assert file_metadata.processed
        assert not file_metadata.has_errors
        assert file_metadata.title == "Test"
        assert "word_count" in file_metadata.metadata

class TestDocumentHandlerPDFExtraction:
    """Tests for the DocumentHandler PDF processing."""
    
    @pytest.fixture
    async def document_handler(self, mock_config):
        """Create a DocumentHandler instance for testing."""
        return DocumentHandler(mock_config)
    
    @pytest.mark.requires_state
    async def test_pdf_text_extraction(self, document_handler, test_data_dir):
        """Test extracting text from PDF file."""
        # Set up test file
        test_file = test_data_dir / "input" / "documents" / "sample.pdf"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        # TODO: Create a sample PDF file

        # Create metadata
        file_metadata = FileMetadata(file_path=test_file)
        file_metadata.add_output_file(test_data_dir / "output" / "test.parsed.md")

        # Process file
        await document_handler.process(test_file, file_metadata)

        # Verify output
        assert file_metadata.processed
        assert not file_metadata.has_errors
        assert len(file_metadata.output_files) > 0
    
    @pytest.mark.requires_state
    async def test_pdf_metadata_update(self, document_handler, test_data_dir):
        """Test metadata updates during PDF processing."""
        # Set up test file
        test_file = test_data_dir / "input" / "documents" / "sample.pdf"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        # TODO: Create a sample PDF file

        # Create metadata
        file_metadata = FileMetadata(file_path=test_file)
        file_metadata.add_output_file(test_data_dir / "output" / "test.parsed.md")

        # Process file
        await document_handler.process(test_file, file_metadata)

        # Verify metadata updates
        assert file_metadata.processed
        assert not file_metadata.has_errors
        assert "page_count" in file_metadata.metadata
        assert "author" in file_metadata.metadata
        assert "creation_date" in file_metadata.metadata
    
    @pytest.mark.requires_state
    async def test_pdf_error_handling(self, document_handler, test_data_dir):
        """Test error handling during PDF processing."""
        # Set up test file
        test_file = test_data_dir / "input" / "documents" / "invalid.pdf"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_bytes(b"Invalid PDF content")

        # Create metadata
        file_metadata = FileMetadata(file_path=test_file)
        file_metadata.add_output_file(test_data_dir / "output" / "test.parsed.md")

        # Process file
        with pytest.raises(Exception) as exc_info:
            await document_handler.process(test_file, file_metadata)

        # Verify error handling
        assert "PDF" in str(exc_info.value)
        assert not file_metadata.processed
        assert file_metadata.has_errors

class TestImageHandlerHeicConversion:
    """Tests for the ImageHandler HEIC conversion."""
    
    @pytest.fixture
    async def image_handler(self, mock_config, use_openai_api, mock_openai_response):
        """Create an ImageHandler instance for testing."""
        handler = ImageHandler(mock_config)
        if not use_openai_api:
            # Mock the OpenAI API methods
            handler._analyze_image = lambda *args, **kwargs: mock_openai_response["image_analysis"]
        return handler
    
    @pytest.mark.requires_state
    async def test_heic_conversion(self, image_handler, input_dir: Path, output_dir: Path, mock_file_metadata: dict, tmp_path: Path):
        """Test HEIC to JPEG conversion process."""
        # Create a mock HEIC file (since we can't include large binary files in tests)
        heic_file = tmp_path / "test.heic"
        heic_file.write_bytes(b"HEIC\x00" + b"\x00" * 100)  # Mock HEIC header
        
        # Set up metadata
        mock_file_metadata["input_path"] = heic_file
        mock_file_metadata["output_path"] = output_dir / "test.jpg"
        
        # Process the HEIC file
        await image_handler.process(
            content=heic_file.read_bytes(),
            file_metadata=mock_file_metadata,
            referenced_files={}
        )
        
        # Verify metadata updates
        assert mock_file_metadata["content_type"] == "image/jpeg"
        assert mock_file_metadata["image_format"] == "JPEG"
        assert mock_file_metadata["original_format"] == "HEIC"
        assert mock_file_metadata["conversion_applied"] is True
    
    @pytest.mark.requires_state
    async def test_jpeg_passthrough(self, image_handler, input_dir: Path, output_dir: Path, mock_file_metadata: dict):
        """Test that JPEG files are passed through without conversion."""
        # Load test JPEG
        test_file = input_dir / "images" / "test.jpg"
        with open(test_file, "rb") as f:
            content = f.read()
        
        # Process the JPEG
        await image_handler.process(
            content=content,
            file_metadata=mock_file_metadata,
            referenced_files={}
        )
        
        # Verify metadata updates
        assert mock_file_metadata["content_type"] == "image/jpeg"
        assert mock_file_metadata["image_format"] == "JPEG"
        assert mock_file_metadata["original_format"] == "JPEG"
        assert mock_file_metadata["conversion_applied"] is False
        
        # Verify image dimensions are captured
        assert mock_file_metadata["image_width"] > 0
        assert mock_file_metadata["image_height"] > 0
    
    @pytest.mark.requires_state
    async def test_image_analysis_disabled(self, image_handler, input_dir: Path, mock_file_metadata: dict):
        """Test that image analysis placeholder is added when OpenAI API is disabled."""
        # Load test image
        test_file = input_dir / "images" / "test.jpg"
        with open(test_file, "rb") as f:
            content = f.read()
        
        # Process the image with OpenAI API disabled
        mock_file_metadata["openai_api_key"] = None
        await image_handler.process(
            content=content,
            file_metadata=mock_file_metadata,
            referenced_files={}
        )
        
        # Verify placeholder analysis is added
        assert mock_file_metadata["image_analysis"] == "Image analysis not available (OpenAI API disabled)"
        assert mock_file_metadata["has_analysis"] is False
    
    @pytest.mark.requires_state
    @pytest.mark.skipif("not config.getoption('--openai-api')")
    async def test_image_analysis_with_api(self, image_handler, input_dir: Path, mock_file_metadata: dict):
        """Test image analysis using actual OpenAI API.
        
        Only runs when --openai-api flag is provided.
        """
        # Load test image
        test_file = input_dir / "images" / "test.jpg"
        with open(test_file, "rb") as f:
            content = f.read()
        
        # Process the image with OpenAI API enabled
        mock_file_metadata["openai_api_key"] = os.getenv("OPENAI_API_KEY")
        await image_handler.process(
            content=content,
            file_metadata=mock_file_metadata,
            referenced_files={}
        )
        
        # Verify analysis is performed
        assert mock_file_metadata["image_analysis"] is not None
        assert mock_file_metadata["image_analysis"] != ""
        assert mock_file_metadata["has_analysis"] is True
        assert len(mock_file_metadata["image_analysis"]) > 50  # Expect meaningful analysis
    
    @pytest.mark.requires_state
    async def test_image_analysis_mocked(self, image_handler, input_dir: Path, mock_file_metadata: dict, mock_openai_response):
        """Test image analysis using mocked OpenAI API."""
        # Load test image
        test_file = input_dir / "images" / "test.jpg"
        with open(test_file, "rb") as f:
            content = f.read()
        
        # Process the image with mocked API
        mock_file_metadata["openai_api_key"] = "mock_key"
        await image_handler.process(
            content=content,
            file_metadata=mock_file_metadata,
            referenced_files={}
        )
        
        # Verify mock analysis is used
        assert mock_file_metadata["image_analysis"] == mock_openai_response["image_analysis"]
        assert mock_file_metadata["has_analysis"] is True
    
    @pytest.mark.requires_state
    async def test_error_handling(self, image_handler, mock_file_metadata: dict, tmp_path: Path):
        """Test handling of corrupted or invalid images."""
        # Create an invalid image file
        invalid_image = tmp_path / "invalid.jpg"
        invalid_image.write_bytes(b"This is not a valid image file")
        
        # Attempt to process invalid image
        with pytest.raises(Exception) as exc_info:
            await image_handler.process(
                content=invalid_image.read_bytes(),
                file_metadata=mock_file_metadata,
                referenced_files={}
            )
        
        # Verify error handling
        assert "image" in str(exc_info.value).lower()
        assert mock_file_metadata["processing_errors"] > 0
        assert mock_file_metadata["has_analysis"] is False 