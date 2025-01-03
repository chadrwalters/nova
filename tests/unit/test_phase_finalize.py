"""Unit tests for the Finalize phase."""
import pytest
from pathlib import Path
from nova.phases.finalize import FinalizePhase
from nova.core.metadata import FileMetadata
from tests.conftest import PipelineState
from nova.core.pipeline import NovaPipeline

class TestFinalizePhase:
    """Tests for the FinalizePhase functionality."""
    
    @pytest.fixture
    async def finalize_phase(self, mock_config):
        """Create a FinalizePhase instance for testing."""
        pipeline = NovaPipeline(mock_config)
        return FinalizePhase(mock_config, pipeline)
    
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
    async def test_basic_finalization(self, finalize_phase, pipeline_state):
        """Test basic content finalization with summary and notes."""
        # Set up summary file
        summary_content = """# Test Document Summary
This is a test summary with key points."""
        
        # Set up notes file
        notes_content = """# Test Document Notes
## Section 1
These are the detailed notes.

## Section 2
More detailed information."""
        
        # Create test files
        summary_file = pipeline_state.output_dir / "test.summary.md"
        notes_file = pipeline_state.output_dir / "test.split.md"
        summary_file.write_text(summary_content)
        notes_file.write_text(notes_content)
        
        file_metadata = FileMetadata(file_path=summary_file)
        output_file = pipeline_state.output_dir / "test.final.md"
        file_metadata.add_output_file(output_file)
        pipeline_state.file_metadata[str(summary_file)] = file_metadata
        
        # Process file
        await finalize_phase.process_file(summary_file, pipeline_state.output_dir)
        
        # Verify output file exists
        assert output_file.exists()
        
        # Check content organization
        final_content = output_file.read_text()
        assert "Test Document Summary" in final_content
        assert "Test Document Notes" in final_content
        assert "Section 1" in final_content
        assert "Section 2" in final_content
    
    @pytest.mark.requires_state
    async def test_attachment_handling(self, finalize_phase, pipeline_state):
        """Test handling of attachments in final output."""
        # Set up content with attachments
        content = """# Test Document

## Content
Here's an image: ![Test Image](ATTACH:images/test.jpg)
And a PDF: [Sample PDF](ATTACH:documents/sample.pdf)

## Attachments
- test.jpg
- sample.pdf"""
        
        # Create test file
        test_file = pipeline_state.output_dir / "test.split.md"
        test_file.write_text(content)
        
        # Set up referenced files
        img_metadata = FileMetadata(file_path=pipeline_state.input_dir / "images" / "test.jpg")
        img_output = pipeline_state.output_dir / "assets" / "images" / "test.jpg"
        img_metadata.add_output_file(img_output)
        
        pdf_metadata = FileMetadata(file_path=pipeline_state.input_dir / "documents" / "sample.pdf")
        pdf_output = pipeline_state.output_dir / "assets" / "documents" / "sample.pdf"
        pdf_metadata.add_output_file(pdf_output)
        
        file_metadata = FileMetadata(file_path=test_file)
        output_file = pipeline_state.output_dir / "test.final.md"
        file_metadata.add_output_file(output_file)
        
        pipeline_state.file_metadata.update({
            str(file_metadata.file_path): file_metadata,
            str(img_metadata.file_path): img_metadata,
            str(pdf_metadata.file_path): pdf_metadata
        })
        
        # Process file
        await finalize_phase.process_file(test_file, pipeline_state.output_dir)
        
        # Verify attachments section
        final_content = output_file.read_text()
        
        assert "## Attachments" in final_content
        assert "test.jpg" in final_content
        assert "sample.pdf" in final_content
        assert "ATTACH:images/test.jpg" in final_content
        assert "ATTACH:documents/sample.pdf" in final_content
    
    @pytest.mark.requires_state
    async def test_metadata_consolidation(self, finalize_phase, pipeline_state):
        """Test consolidation of metadata in final output."""
        # Set up test files with metadata
        summary_content = """# Test Summary
Key points about the document."""
        
        notes_content = """# Test Notes
## Code Section
```python
def test():
    pass
```

## Data Section
- Point 1
- Point 2"""
        
        # Create test files
        summary_file = pipeline_state.output_dir / "test.summary.md"
        notes_file = pipeline_state.output_dir / "test.split.md"
        summary_file.write_text(summary_content)
        notes_file.write_text(notes_content)
        
        file_metadata = FileMetadata(file_path=summary_file)
        output_file = pipeline_state.output_dir / "test.final.md"
        file_metadata.add_output_file(output_file)
        file_metadata.metadata.update({
            "word_count": 50,
            "has_code_blocks": True,
            "language_stats": {"python": 1}
        })
        
        pipeline_state.file_metadata[str(summary_file)] = file_metadata
        
        # Process file
        await finalize_phase.process_file(summary_file, pipeline_state.output_dir)
        
        # Verify metadata file
        metadata_file = pipeline_state.output_dir / "test.metadata.json"
        assert metadata_file.exists()
        
        # Check metadata content
        import json
        metadata = json.loads(metadata_file.read_text())
        assert metadata["metadata"]["word_count"] == 50
        assert metadata["metadata"]["has_code_blocks"] is True
        assert metadata["metadata"]["language_stats"]["python"] == 1
    
    @pytest.mark.requires_state
    async def test_table_of_contents(self, finalize_phase, pipeline_state):
        """Test generation of table of contents."""
        # Set up content with multiple sections
        content = """# Test Document

## Introduction
Introduction text.

## Methods
### Data Collection
Collection details.

### Analysis
Analysis details.

## Results
Result details.

## Conclusion
Concluding remarks."""
        
        # Create test file
        test_file = pipeline_state.output_dir / "test.split.md"
        test_file.write_text(content)
        
        file_metadata = FileMetadata(file_path=test_file)
        output_file = pipeline_state.output_dir / "test.final.md"
        file_metadata.add_output_file(output_file)
        
        # Process file
        await finalize_phase.process_file(test_file, pipeline_state.output_dir)
        
        # Verify table of contents
        final_content = output_file.read_text()
        
        assert "## Table of Contents" in final_content
        assert "- [Introduction](#introduction)" in final_content
        assert "- [Methods](#methods)" in final_content
        assert "  - [Data Collection](#data-collection)" in final_content
        assert "  - [Analysis](#analysis)" in final_content
        assert "- [Results](#results)" in final_content
        assert "- [Conclusion](#conclusion)" in final_content
    
    @pytest.mark.requires_state
    async def test_error_handling(self, finalize_phase, pipeline_state):
        """Test error handling during finalization."""
        # Set up metadata with errors
        file_metadata = FileMetadata(file_path=pipeline_state.input_dir / "test.md")
        output_file = pipeline_state.output_dir / "test.final.md"
        file_metadata.add_output_file(output_file)
        file_metadata.add_error("handler1", "Error 1")
        file_metadata.add_error("handler2", "Error 2")
        
        pipeline_state.file_metadata[str(file_metadata.file_path)] = file_metadata
        
        # Process file
        await finalize_phase.process_file(file_metadata.file_path, pipeline_state.output_dir)
        
        # Verify error section in output
        final_content = output_file.read_text()
        
        assert "## Processing Errors" in final_content
        assert "Error 1" in final_content
        assert "Error 2" in final_content
        
        # Check error status in metadata
        assert file_metadata.metadata.get("phase_status", {}).get("finalize") == "completed_with_errors" 