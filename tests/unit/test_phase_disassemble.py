"""Unit tests for the Disassemble phase."""
import pytest
from pathlib import Path
from nova.phases.disassemble import DisassemblyPhase
from nova.core.metadata import FileMetadata
from tests.conftest import PipelineState

class TestDisassemblyPhase:
    """Tests for the DisassemblyPhase functionality."""
    
    @pytest.fixture
    async def disassembly_phase(self, mock_config):
        """Create a DisassemblyPhase instance for testing."""
        return DisassemblyPhase(mock_config)
    
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
    async def test_basic_disassembly(self, disassembly_phase, pipeline_state, input_dir: Path):
        """Test basic content disassembly with summary and notes."""
        # Set up test file with summary and notes
        content = """# Test Document

## Summary
This is a test summary.

## Notes
These are test notes.
- Note point 1
- Note point 2

## Additional Info
Some additional information."""

        # Create test file
        test_file = pipeline_state.output_dir / "test.parsed.md"
        test_file.write_text(content)
        
        file_metadata = FileMetadata(file_path=test_file)
        file_metadata.add_output_file(pipeline_state.output_dir / "test.disassembled.md")
        pipeline_state.file_metadata[str(test_file)] = file_metadata
        
        # Process file
        await disassembly_phase.process_file(test_file, pipeline_state.output_dir)
        
        # Verify output files exist
        summary_file = pipeline_state.output_dir / "test.summary.md"
        notes_file = pipeline_state.output_dir / "test.notes.md"
        assert summary_file.exists()
        assert notes_file.exists()
        
        # Check content separation
        summary_content = summary_file.read_text()
        notes_content = notes_file.read_text()
        
        assert "This is a test summary" in summary_content
        assert "Note point 1" in notes_content
        assert "Note point 2" in notes_content
        assert "Additional Info" in notes_content
    
    @pytest.mark.requires_state
    async def test_no_explicit_sections(self, disassembly_phase, pipeline_state):
        """Test disassembly of content without explicit sections."""
        # Set up test file without explicit sections
        content = """# Test Document

This is some content without explicit sections.
It should all go into notes.

- Point 1
- Point 2"""

        # Create test file
        test_file = pipeline_state.output_dir / "test.parsed.md"
        test_file.write_text(content)
        
        file_metadata = FileMetadata(file_path=test_file)
        file_metadata.add_output_file(pipeline_state.output_dir / "test.disassembled.md")
        pipeline_state.file_metadata[str(test_file)] = file_metadata
        
        # Process file
        await disassembly_phase.process_file(test_file, pipeline_state.output_dir)
        
        # Verify output files exist
        summary_file = pipeline_state.output_dir / "test.summary.md"
        notes_file = pipeline_state.output_dir / "test.notes.md"
        assert summary_file.exists()
        assert notes_file.exists()
        
        # Check content placement
        summary_content = summary_file.read_text()
        notes_content = notes_file.read_text()
        
        assert summary_content.strip() == ""  # Summary should be empty
        assert "without explicit sections" in notes_content
        assert "Point 1" in notes_content
        assert "Point 2" in notes_content
    
    @pytest.mark.requires_state
    async def test_multiple_summary_sections(self, disassembly_phase, pipeline_state):
        """Test handling of multiple summary sections."""
        # Set up test file with multiple summary sections
        content = """# Test Document

## Summary
First summary section.

## Notes
Some notes.

## Executive Summary
Second summary section.

## More Notes
More notes here."""

        # Create test file
        test_file = pipeline_state.output_dir / "test.parsed.md"
        test_file.write_text(content)
        
        file_metadata = FileMetadata(file_path=test_file)
        file_metadata.add_output_file(pipeline_state.output_dir / "test.disassembled.md")
        pipeline_state.file_metadata[str(test_file)] = file_metadata
        
        # Process file
        await disassembly_phase.process_file(test_file, pipeline_state.output_dir)
        
        # Verify output files exist
        summary_file = pipeline_state.output_dir / "test.summary.md"
        notes_file = pipeline_state.output_dir / "test.notes.md"
        assert summary_file.exists()
        assert notes_file.exists()
        
        # Check content combination
        summary_content = summary_file.read_text()
        notes_content = notes_file.read_text()
        
        assert "First summary section" in summary_content
        assert "Second summary section" in summary_content
        assert "Some notes" in notes_content
        assert "More notes" in notes_content
    
    @pytest.mark.requires_state
    async def test_code_block_preservation(self, disassembly_phase, pipeline_state):
        """Test preservation of code blocks during disassembly."""
        # Set up test file with code blocks
        content = """# Test Document

## Code Section
Here's some code:
```python
def test_function():
    return "test"
```

## Another Section
More code:
```javascript
function anotherTest() {
    console.log("test");
}
```"""

        # Create test file
        test_file = pipeline_state.output_dir / "test.parsed.md"
        test_file.write_text(content)
        
        file_metadata = FileMetadata(file_path=test_file)
        file_metadata.add_output_file(pipeline_state.output_dir / "test.disassembled.md")
        pipeline_state.file_metadata[str(test_file)] = file_metadata
        
        # Process file
        await disassembly_phase.process_file(test_file, pipeline_state.output_dir)
        
        # Verify code blocks are preserved
        split_file = pipeline_state.output_dir / "test.split.md"
        split_content = split_file.read_text()
        
        assert "```python" in split_content
        assert "def test_function()" in split_content
        assert "```javascript" in split_content
        assert "function anotherTest()" in split_content
    
    @pytest.mark.requires_state
    async def test_metadata_tracking(self, disassembly_phase, pipeline_state):
        """Test metadata updates during disassembly."""
        # Set up test file
        content = """# Test Document

## Section 1
Content 1

## Section 2
Content 2"""

        # Create test file
        test_file = pipeline_state.output_dir / "test.parsed.md"
        test_file.write_text(content)
        
        file_metadata = FileMetadata(file_path=test_file)
        file_metadata.add_output_file(pipeline_state.output_dir / "test.disassembled.md")
        pipeline_state.file_metadata[str(test_file)] = file_metadata
        
        # Process file
        await disassembly_phase.process_file(test_file, pipeline_state.output_dir)
        
        # Verify metadata updates
        assert file_metadata.section_count == 2
        assert file_metadata.phase_status["disassemble"] == "completed"
        assert file_metadata.is_processed
        assert not file_metadata.processing_errors
    
    @pytest.mark.requires_state
    async def test_list_preservation(self, disassembly_phase, pipeline_state):
        """Test preservation of list structures during disassembly."""
        # Set up test file with various list types
        content = """# Test Document

## Ordered Lists
1. First item
2. Second item
   1. Sub-item 1
   2. Sub-item 2

## Unordered Lists
- Item A
- Item B
  - Sub-item X
  - Sub-item Y

## Mixed Lists
1. Top level
   - Sub bullet
   - Another bullet
2. Second level
   1. Numbered sub-item
   2. Another numbered"""

        # Create test file
        test_file = pipeline_state.output_dir / "test.parsed.md"
        test_file.write_text(content)
        
        file_metadata = FileMetadata(file_path=test_file)
        file_metadata.add_output_file(pipeline_state.output_dir / "test.disassembled.md")
        pipeline_state.file_metadata[str(test_file)] = file_metadata
        
        # Process file
        await disassembly_phase.process_file(test_file, pipeline_state.output_dir)
        
        # Verify list structures
        split_file = pipeline_state.output_dir / "test.split.md"
        split_content = split_file.read_text()
        
        # Check ordered lists
        assert "1. First item" in split_content
        assert "2. Second item" in split_content
        assert "   1. Sub-item 1" in split_content
        
        # Check unordered lists
        assert "- Item A" in split_content
        assert "- Item B" in split_content
        assert "  - Sub-item X" in split_content
        
        # Check mixed lists
        assert "1. Top level" in split_content
        assert "   - Sub bullet" in split_content
        assert "2. Second level" in split_content 