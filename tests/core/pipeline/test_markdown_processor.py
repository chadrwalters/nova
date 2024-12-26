import os
import pytest
from pathlib import Path
from typing import Dict, Any

from nova.phases.parse.handlers.markdown.markdown_handler import MarkdownHandler
from nova.phases.parse.processor import MarkdownProcessor
from nova.core.config.base import (
    PipelineConfig,
    ProcessorConfig,
    PathConfig,
    ComponentConfig,
    HandlerConfig
)

TEST_DATA_DIR = Path("tests/data")
MARKDOWN_DIR = TEST_DATA_DIR / "markdown"
ATTACHMENTS_DIR = TEST_DATA_DIR / "attachments"

def get_test_file_path(filename):
    """Helper to get full path for test files."""
    return MARKDOWN_DIR / filename

@pytest.fixture
def processor_config():
    """Create a basic processor configuration for testing."""
    return ProcessorConfig(
        name="MARKDOWN_PARSE",
        description="Parse markdown files",
        output_dir=str(TEST_DATA_DIR / "output"),
        processor="MarkdownProcessor",
        components={
            "markdown_processor": ComponentConfig(
                parser="markitdown==0.0.1a3",
                config={
                    "document_conversion": True,
                    "image_processing": True,
                    "metadata_preservation": True
                },
                handlers=[
                    HandlerConfig(
                        type="MarkdownHandler",
                        base_handler="nova.phases.core.base_handler.BaseHandler",
                        document_conversion=True,
                        image_processing=True,
                        metadata_preservation=True
                    )
                ]
            )
        }
    )

@pytest.fixture
def pipeline_config(processor_config):
    """Create a basic pipeline configuration for testing."""
    return PipelineConfig(
        paths=PathConfig(
            base_dir=str(TEST_DATA_DIR)
        ),
        phases=[processor_config],
        input_dir=str(TEST_DATA_DIR),
        output_dir=str(TEST_DATA_DIR / "output"),
        processing_dir=str(TEST_DATA_DIR / "processing"),
        temp_dir=str(TEST_DATA_DIR / "temp")
    )

@pytest.fixture
def markdown_processor(processor_config, pipeline_config):
    """Create a markdown processor instance for testing."""
    return MarkdownProcessor(processor_config, pipeline_config)

@pytest.fixture
def markdown_handler():
    """Create a markdown handler instance for testing."""
    return MarkdownHandler()

@pytest.fixture
def processor(markdown_processor):
    """Create processor instance for testing."""
    return markdown_processor

@pytest.mark.asyncio
async def test_simple_markdown_processing(markdown_processor):
    """Test processing of simple markdown with basic formatting."""
    input_file = get_test_file_path("01_simple_markdown.md")
    assert input_file.exists(), f"Test file not found: {input_file}"
    
    await markdown_processor.setup()
    result = await markdown_processor.process(input_file, {})
    assert result is not None
    assert result.success
    assert "Simple Test Document" in result.content
    assert "Section One" in result.content
    assert "Section Two" in result.content

@pytest.mark.asyncio
async def test_nested_sections_processing(markdown_processor):
    """Test processing of markdown with nested sections and complex structure."""
    input_file = get_test_file_path("02_nested_sections.md")
    assert input_file.exists(), f"Test file not found: {input_file}"
    
    await markdown_processor.setup()
    result = await markdown_processor.process(input_file, {})
    assert result is not None
    assert result.success
    assert "Document with Nested Sections" in result.content
    assert "Subsection A" in result.content
    assert "Subsection B" in result.content
    assert "Deep Nested Section" in result.content
    
    # Verify nested list structure is preserved
    assert "Main point 1" in result.content
    assert "Sub point 1.1" in result.content
    assert "Sub-sub point 1.2.1" in result.content

@pytest.mark.asyncio
async def test_images_and_references(markdown_processor):
    """Test processing of markdown with images and reference links."""
    input_file = get_test_file_path("03_images_and_references.md")
    assert input_file.exists(), f"Test file not found: {input_file}"
    
    await markdown_processor.setup()
    result = await markdown_processor.process(input_file, {})
    assert result is not None
    assert result.success
    
    # Verify image references are processed
    assert "jpg_test.jpg" in result.content
    assert "png_test.png" in result.content
    
    # Check reference links
    assert "[Referenced Image]" in result.content
    assert "reference-link.com" in result.content

@pytest.mark.asyncio
async def test_attachments_processing(markdown_processor):
    """Test processing of markdown with various attachment types."""
    input_file = get_test_file_path("04_attachments.md")
    assert input_file.exists(), f"Test file not found: {input_file}"
    
    await markdown_processor.setup()
    result = await markdown_processor.process(input_file, {})
    assert result is not None
    assert result.success
    
    # Verify attachment references
    assert "pdf_test.pdf" in result.content
    assert "word_test.docx" in result.content
    assert "xlsx_test.xlsx" in result.content

@pytest.mark.asyncio
async def test_complex_document_processing(processor):
    """Test processing of a complex markdown document."""
    input_file = Path("tests/data/markdown/05_complex_document.md")
    assert input_file.exists(), f"Test file not found: {input_file}"
    
    await processor.setup()
    result = await processor.process(input_file, {})
    assert result.success

    # Check basic content is present
    assert "Complex Document Example" in result.content
    assert "Overview" in result.content
    assert "Technical Details" in result.content

    # Check code blocks are preserved
    assert "```python" in result.content
    assert "def process_markdown" in result.content
    assert "```json" in result.content

    # Check image references
    assert "![Architecture Overview]" in result.content
    assert "![Diagram]" in result.content
    assert "![Final]" in result.content

    # Check links
    assert "[Implementation Guide]" in result.content
    assert "[API Documentation]" in result.content

    # Check table is preserved
    assert "| Feature | Status | Notes |" in result.content
    assert "| Parsing | ✅ | Basic functionality |" in result.content

    # Check metadata
    assert result.metadata is not None
    assert "frontmatter" in result.metadata
    assert result.metadata["frontmatter"]["title"] == "Complex Test Document"
    assert result.metadata["frontmatter"]["author"] == "Test User"
    assert result.metadata["frontmatter"]["tags"] == ["test", "markdown", "complex"]

    # Check content markers
    assert "content_markers" in result.metadata
    assert "images" in result.metadata["content_markers"]
    assert len(result.metadata["content_markers"]["images"]) == 3  # Three images in the document
    assert "code_blocks" in result.metadata["content_markers"]
    assert len(result.metadata["content_markers"]["code_blocks"]) == 2  # Two code blocks 