"""
Unit tests for Nova parse phase.
"""
import pytest
import asyncio
from pathlib import Path
from PIL import Image
from reportlab.pdfgen import canvas
from unittest.mock import Mock, MagicMock

from nova.phases.parse import ParsePhase
from nova.handlers.markdown import MarkdownHandler
from nova.handlers.document import DocumentHandler
from nova.handlers.image import ImageHandler
from nova.config.settings import NovaConfig, CacheConfig, APIConfig, OpenAIConfig


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Test image description"))]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_image_handler(nova_config, mock_openai_client):
    """Create a mock image handler with OpenAI client."""
    handler = ImageHandler(nova_config)
    handler.vision_client = mock_openai_client
    return handler


@pytest.fixture
def nova_config(mock_fs):
    """Create test configuration."""
    config = NovaConfig(
        base_dir=str(mock_fs["root"]),
        input_dir=str(mock_fs["input"]),
        output_dir=str(mock_fs["output"]),
        processing_dir=str(mock_fs["processing"]),
        cache=CacheConfig(
            dir=str(mock_fs["cache"]),
            enabled=True,
            ttl=3600
        ),
        apis=APIConfig(
            openai=OpenAIConfig(
                api_key="test_key",
                model="gpt-4o",
                max_tokens=300
            )
        )
    )
    return config


@pytest.fixture
def mock_pipeline(mock_fs):
    """Create a mock pipeline."""
    pipeline = MagicMock()
    pipeline.name = "test"
    pipeline.state = {"parse": {"skipped_files": set()}}
    pipeline.output_manager = MagicMock()
    pipeline.output_manager.get_output_path_for_phase.return_value = mock_fs["output"] / "test.md"
    return pipeline


@pytest.fixture
def test_state(nova_config, mock_fs):
    """Create test state."""
    # Create mock pipeline
    mock_pipeline = Mock()
    mock_pipeline.name = "test"
    mock_pipeline.state = {
        "parse": {
            "skipped_files": set(),
            "processed_files": set(),
            "errors": []
        }
    }

    # Create mock output manager
    mock_output_manager = Mock()
    def get_output_path_for_phase(input_file, phase_name, extension):
        input_file = Path(input_file)
        return mock_fs["output"] / f"{input_file.stem}{extension}"
    mock_output_manager.get_output_path_for_phase.side_effect = get_output_path_for_phase

    # Configure mock pipeline
    mock_pipeline.output_manager = mock_output_manager
    mock_pipeline.config = nova_config

    return {
        "skipped_files": set(),
        "processed_files": set(),
        "errors": [],
        "metrics": {},
        "config": nova_config,
        "pipeline": mock_pipeline
    }


@pytest.mark.unit
@pytest.mark.phases
class TestParsePhase:
    """Test parse phase functionality."""
    
    async def test_parse_markdown(self, mock_fs, test_state):
        """Test parsing markdown files."""
        # Create test markdown file
        test_file = mock_fs["input"] / "test.md"
        test_file.write_text("# Test Document\n\nThis is a test markdown file.")
        
        # Set up parse phase
        phase = ParsePhase(test_state["config"], test_state["pipeline"])
        phase.registry.register_handler(MarkdownHandler)
        
        # Process the file
        result = await phase.process_file(test_file, mock_fs["output"])
        
        # Verify results
        assert result is not None
        assert result.processed is True
        assert result.title == "test"
        assert len(result.output_files) == 1
        
        # Check output content
        output_file = mock_fs["output"] / "test.parsed.md"
        assert output_file.exists()
        content = output_file.read_text()
        assert "# Test Document" in content
        assert "This is a test markdown file." in content
    
    async def test_parse_pdf(self, mock_fs, test_state):
        """Test parsing PDF files."""
        # Create test PDF file
        test_file = mock_fs["input"] / "test.pdf"
        c = canvas.Canvas(str(test_file))
        c.drawString(100, 750, "Test PDF Content")
        c.save()
        
        # Set up parse phase
        phase = ParsePhase(test_state["config"], test_state["pipeline"])
        phase.registry.register_handler(DocumentHandler)
        
        # Process the file
        result = await phase.process_file(test_file, mock_fs["output"])
        
        # Verify results
        assert result is not None
        assert result.processed is True
        assert result.title == "test"
        assert len(result.output_files) == 1
        
        # Check output content
        output_file = mock_fs["output"] / "test.parsed.md"
        assert output_file.exists()
        content = output_file.read_text()
        assert "Test PDF Content" in content
    
    async def test_parse_image(self, mock_fs, test_state, mock_image_handler):
        """Test parsing image files."""
        # Create test image file
        test_file = mock_fs["input"] / "test.jpg"
        img = Image.new('RGB', (100, 100), color='red')
        img.save(test_file)

        # Set up parse phase with mocked handler
        phase = ParsePhase(test_state["config"], test_state["pipeline"])
        phase.registry.handlers["jpg"] = mock_image_handler

        # Process the file
        result = await phase.process_file(test_file, mock_fs["output"])

        # Verify results
        assert result is not None
        assert result.processed is True
        assert result.title == "test"
        assert len(result.output_files) == 1

        # Check output content
        output_file = mock_fs["output"] / "test.parsed.md"
        assert output_file.exists()
        content = output_file.read_text()
        assert "Test image description" in content
    
    async def test_parse_multiple_files(self, mock_fs, test_state, mock_image_handler):
        """Test parsing multiple files concurrently."""
        # Create test files
        files = {
            "markdown": mock_fs["input"] / "test1.md",
            "pdf": mock_fs["input"] / "test2.pdf",
            "image": mock_fs["input"] / "test3.jpg"
        }
        
        # Create content
        files["markdown"].write_text("# Test Markdown")
        c = canvas.Canvas(str(files["pdf"]))
        c.drawString(100, 750, "Test PDF")
        c.save()
        img = Image.new('RGB', (100, 100), color='red')
        img.save(files["image"])
        
        # Set up parse phase
        phase = ParsePhase(test_state["config"], test_state["pipeline"])
        phase.registry.register_handler(MarkdownHandler)
        phase.registry.register_handler(DocumentHandler)
        phase.registry.handlers["jpg"] = mock_image_handler
        
        # Process files concurrently
        tasks = [phase.process_file(file_path, mock_fs["output"]) for file_path in files.values()]
        results = await asyncio.gather(*tasks)
        
        # Verify results
        assert all(result is not None for result in results)
        assert all(result.processed is True for result in results)
        assert all(len(result.output_files) == 1 for result in results)
        
        # Check output files
        output_files = {
            "markdown": mock_fs["output"] / "test1.parsed.md",
            "pdf": mock_fs["output"] / "test2.parsed.md",
            "image": mock_fs["output"] / "test3.parsed.md"
        }
        
        for file_path in output_files.values():
            assert file_path.exists()
    
    async def test_parse_error_handling(self, mock_fs, test_state, mock_image_handler):
        """Test error handling during parsing."""
        # Create corrupted/invalid files
        files = {
            "invalid_pdf": mock_fs["input"] / "invalid.pdf",
            "empty_md": mock_fs["input"] / "empty.md",
            "corrupted_img": mock_fs["input"] / "corrupted.jpg"
        }

        # Create invalid content
        files["invalid_pdf"].write_text("Not a PDF file")
        files["empty_md"].write_text("")
        files["corrupted_img"].write_text("Not an image")

        # Set up parse phase
        phase = ParsePhase(test_state["config"], test_state["pipeline"])
        phase.registry.register_handler(MarkdownHandler)
        phase.registry.register_handler(DocumentHandler)
        phase.registry.handlers["jpg"] = mock_image_handler

        # Process files and check error handling
        for file_path in files.values():
            result = await phase.process_file(file_path, mock_fs["output"])

            if result is not None:
                if file_path.suffix == '.md':
                    # Empty markdown files are valid
                    assert result.processed is True
                    assert len(result.errors) == 0
                else:
                    # Invalid files should have errors
                    assert result.processed is False
                    assert result.has_errors is True
                    assert len(result.errors) > 0
                    assert result.errors.get(file_path.suffix.lstrip('.')) is not None
    
    async def test_parse_svg(self, mock_fs, test_state, mock_image_handler):
        """Test parsing SVG files."""
        # Create test SVG file
        test_file = mock_fs["input"] / "test.svg"
        svg_content = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect width="100" height="100" fill="red"/>
</svg>"""
        test_file.write_text(svg_content)

        # Set up parse phase
        phase = ParsePhase(test_state["config"], test_state["pipeline"])
        phase.registry.handlers["svg"] = mock_image_handler

        # Process the file
        result = await phase.process_file(test_file, mock_fs["output"])

        # Verify results
        assert result is not None
        assert result.processed is True
        assert result.title == "test"
        assert len(result.output_files) == 1

        # Check output content
        output_file = mock_fs["output"] / "test.parsed.md"
        assert output_file.exists()
        content = output_file.read_text()
        assert "![ATTACH:IMAGE:test]" in content

    async def test_parse_invalid_svg(self, mock_fs, test_state, mock_image_handler):
        """Test parsing invalid SVG files."""
        # Create invalid SVG file with completely invalid XML
        test_file = mock_fs["input"] / "invalid.svg"
        test_file.write_text("""
        <svg xmlns="http://www.w3.org/2000/svg">
            <invalidtag>
            <unclosed>
            <broken
        """)

        # Set up parse phase
        phase = ParsePhase(test_state["config"], test_state["pipeline"])
        phase.registry.handlers["svg"] = mock_image_handler

        # Process the file
        result = await phase.process_file(test_file, mock_fs["output"])

        # For invalid files, we expect None as the result
        assert result is None

        # Verify the file was not created
        output_file = mock_fs["output"] / "invalid.parsed.md"
        assert not output_file.exists() 