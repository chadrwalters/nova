"""Unit tests for the Parse phase."""
import pytest
from pathlib import Path
from nova.phases.parse import ParsePhase
from nova.core.metadata import FileMetadata
from tests.conftest import PipelineState
from nova.core.pipeline import NovaPipeline

class TestParsePhase:
    """Tests for the ParsePhase functionality."""
    
    @pytest.fixture
    async def parse_phase(self, mock_config):
        """Create a ParsePhase instance for testing."""
        pipeline = NovaPipeline(mock_config)
        return ParsePhase(mock_config, pipeline)
    
    @pytest.fixture
    def pipeline_state(self, input_dir: Path, output_dir: Path, processing_dir: Path):
        """Create a PipelineState instance for testing."""
        return PipelineState(
            input_dir=input_dir,
            output_dir=output_dir,
            processing_dir=processing_dir,
            file_metadata={},
            referenced_files={}
        )
    
    @pytest.mark.requires_state
    async def test_parse_markdown(self, parse_phase, pipeline_state, input_dir: Path):
        """Test parsing of markdown files."""
        # Set up test file
        test_file = input_dir / "markdown" / "simple.md"
        file_metadata = FileMetadata(file_path=test_file)
        output_file = pipeline_state.output_dir / "simple.parsed.md"
        file_metadata.add_output_file(output_file)
        pipeline_state.file_metadata[str(test_file)] = file_metadata
        
        # Process file
        await parse_phase.process_file(test_file, pipeline_state.output_dir)
        
        # Verify output file exists
        assert output_file.exists()
        
        # Check content transformations
        content = output_file.read_text()
        assert "# Simple Test Document" in content
        assert "```python" in content
        assert "def test_function():" in content
        
        # Verify metadata updates
        assert file_metadata.metadata.get("word_count", 0) > 0
        assert file_metadata.metadata.get("has_code_blocks", False) is True
        assert file_metadata.metadata.get("language_stats", {}).get("python", 0) > 0
    
    @pytest.mark.requires_state
    async def test_parse_pdf(self, parse_phase, pipeline_state, input_dir: Path):
        """Test parsing of PDF files."""
        # Set up test file
        test_file = input_dir / "documents" / "sample.pdf"
        file_metadata = FileMetadata(file_path=test_file)
        output_file = pipeline_state.output_dir / "sample.parsed.md"
        file_metadata.add_output_file(output_file)
        pipeline_state.file_metadata[str(test_file)] = file_metadata
        
        # Process file
        await parse_phase.process_file(test_file, pipeline_state.output_dir)
        
        # Verify output file exists
        assert output_file.exists()
        
        # Check content transformations
        content = output_file.read_text()
        assert "```pdf-content" in content
        assert "Test Document" in content
        assert "Features:" in content
        
        # Verify metadata updates
        assert file_metadata.metadata.get("word_count", 0) > 0
        assert file_metadata.metadata.get("page_count", 0) == 1
        assert file_metadata.metadata.get("has_text", False) is True
    
    @pytest.mark.requires_state
    async def test_parse_image(self, parse_phase, pipeline_state, input_dir: Path):
        """Test parsing of image files."""
        # Set up test file
        test_file = input_dir / "images" / "test.jpg"
        file_metadata = FileMetadata(file_path=test_file)
        output_file = pipeline_state.output_dir / "test.jpg"
        file_metadata.add_output_file(output_file)
        pipeline_state.file_metadata[str(test_file)] = file_metadata
        
        # Process file
        await parse_phase.process_file(test_file, pipeline_state.output_dir)
        
        # Verify image is processed
        assert file_metadata.metadata.get("content_type") == "image/jpeg"
        assert file_metadata.metadata.get("image_format") == "JPEG"
        assert file_metadata.metadata.get("image_width", 0) > 0
        assert file_metadata.metadata.get("image_height", 0) > 0
    
    @pytest.mark.requires_state
    async def test_parse_multiple_files(self, parse_phase, pipeline_state, input_dir: Path):
        """Test parsing multiple files in a single phase execution."""
        # Set up test files
        md_file = input_dir / "markdown" / "simple.md"
        pdf_file = input_dir / "documents" / "sample.pdf"
        img_file = input_dir / "images" / "test.jpg"
        
        pipeline_state.file_metadata.update({
            str(md_file): FileMetadata(file_path=md_file),
            str(pdf_file): FileMetadata(file_path=pdf_file),
            str(img_file): FileMetadata(file_path=img_file)
        })
        
        # Process each file
        for file_path in [md_file, pdf_file, img_file]:
            await parse_phase.process_file(file_path, pipeline_state.output_dir)
        
        # Verify all files are processed
        assert all(meta.processed for meta in pipeline_state.file_metadata.values())
        assert all(any(output_file.exists() for output_file in meta.output_files) for meta in pipeline_state.file_metadata.values())
    
    @pytest.mark.requires_state
    async def test_error_handling(self, parse_phase, pipeline_state, tmp_path: Path):
        """Test error handling for invalid files."""
        # Create an invalid file
        invalid_file = tmp_path / "invalid.xyz"
        invalid_file.write_text("Invalid content")
        
        file_metadata = FileMetadata(file_path=invalid_file)
        output_file = pipeline_state.output_dir / "invalid.parsed.md"
        file_metadata.add_output_file(output_file)
        pipeline_state.file_metadata[str(invalid_file)] = file_metadata
        
        # Process file
        result = await parse_phase.process_file(invalid_file, pipeline_state.output_dir)
        
        # Verify error handling
        assert result is None  # No handler found for unsupported file type
        assert invalid_file in parse_phase.pipeline.state["parse"]["skipped_files"]
        assert parse_phase.stats[".xyz"]["skipped"] == 1 