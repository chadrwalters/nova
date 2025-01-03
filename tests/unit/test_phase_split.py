"""Unit tests for the Split phase."""
import pytest
from pathlib import Path
from nova.phases.split import SplitPhase
from nova.core.metadata import FileMetadata
from nova.core.pipeline import NovaPipeline
from tests.conftest import PipelineState

class TestSplitPhase:
    """Tests for the SplitPhase functionality."""
    
    @pytest.fixture
    def split_phase(self, mock_config):
        """Create a SplitPhase instance for testing."""
        pipeline = NovaPipeline(mock_config)
        return SplitPhase(mock_config, pipeline)
    
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
    async def test_basic_section_splitting(self, split_phase, pipeline_state):
        """Test basic content splitting by sections."""
        # Set up test file with multiple sections
        content = """# Test Document

## Introduction
This is the introduction.

## Methods
These are the methods:
1. First method
2. Second method

## Results
Here are the results:
- Result 1
- Result 2

## Conclusion
This is the conclusion."""

        # Create test file
        test_file = pipeline_state.output_dir / "test.notes.md"
        test_file.write_text(content)
        
        file_metadata = FileMetadata(file_path=test_file)
        output_file = pipeline_state.output_dir / "test.split.md"
        file_metadata.add_output_file(output_file)
        pipeline_state.file_metadata[str(test_file)] = file_metadata
        
        # Process file
        await split_phase.process_file(test_file, pipeline_state.output_dir)
        
        # Verify output files exist
        assert output_file.exists()
        
        # Check section organization
        split_content = output_file.read_text()
        sections = split_content.split("---")
        
        assert len(sections) >= 4  # At least 4 sections
        assert any("Introduction" in section for section in sections)
        assert any("Methods" in section for section in sections)
        assert any("Results" in section for section in sections)
        assert any("Conclusion" in section for section in sections)
    
    @pytest.mark.requires_state
    async def test_nested_sections(self, split_phase, pipeline_state):
        """Test handling of nested section headings."""
        # Set up test file with nested sections
        content = """# Test Document

## Main Section 1
Main content 1.

### Subsection 1.1
Subsection content 1.1.

### Subsection 1.2
Subsection content 1.2.

## Main Section 2
Main content 2.

### Subsection 2.1
Subsection content 2.1."""

        # Create test file
        test_file = pipeline_state.output_dir / "test.notes.md"
        test_file.write_text(content)
        
        file_metadata = FileMetadata(file_path=test_file)
        output_file = pipeline_state.output_dir / "test.split.md"
        file_metadata.add_output_file(output_file)
        pipeline_state.file_metadata[str(test_file)] = file_metadata
        
        # Process file
        await split_phase.process_file(test_file, pipeline_state.output_dir)
        
        # Verify output structure
        split_content = output_file.read_text()
        
        # Check section hierarchy
        assert "Main Section 1" in split_content
        assert "Subsection 1.1" in split_content
        assert "Subsection 1.2" in split_content
        assert "Main Section 2" in split_content
        assert "Subsection 2.1" in split_content
        
        # Verify subsections are properly nested
        main1_pos = split_content.find("Main Section 1")
        sub11_pos = split_content.find("Subsection 1.1")
        main2_pos = split_content.find("Main Section 2")
        
        assert main1_pos < sub11_pos < main2_pos
    
    @pytest.mark.requires_state
    async def test_code_block_handling(self, split_phase, pipeline_state):
        """Test preservation of code blocks during splitting."""
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
        test_file = pipeline_state.output_dir / "test.notes.md"
        test_file.write_text(content)
        
        file_metadata = FileMetadata(file_path=test_file)
        output_file = pipeline_state.output_dir / "test.split.md"
        file_metadata.add_output_file(output_file)
        pipeline_state.file_metadata[str(test_file)] = file_metadata
        
        # Process file
        await split_phase.process_file(test_file, pipeline_state.output_dir)
        
        # Verify code blocks are preserved
        split_content = output_file.read_text()
        
        assert "```python" in split_content
        assert "def test_function()" in split_content
        assert "```javascript" in split_content
        assert "function anotherTest()" in split_content
    
    @pytest.mark.requires_state
    async def test_list_preservation(self, split_phase, pipeline_state):
        """Test preservation of list structures during splitting."""
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
        test_file = pipeline_state.output_dir / "test.notes.md"
        test_file.write_text(content)
        
        file_metadata = FileMetadata(file_path=test_file)
        output_file = pipeline_state.output_dir / "test.split.md"
        file_metadata.add_output_file(output_file)
        pipeline_state.file_metadata[str(test_file)] = file_metadata
        
        # Process file
        await split_phase.process_file(test_file, pipeline_state.output_dir)
        
        # Verify list structures
        split_content = output_file.read_text()
        
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
    
    @pytest.mark.requires_state
    async def test_metadata_tracking(self, split_phase, pipeline_state):
        """Test metadata updates during splitting."""
        # Set up test file
        content = """# Test Document

## Section 1
Content 1

## Section 2
Content 2"""

        # Create test file
        test_file = pipeline_state.output_dir / "test.notes.md"
        test_file.write_text(content)
        
        file_metadata = FileMetadata(file_path=test_file)
        output_file = pipeline_state.output_dir / "test.split.md"
        file_metadata.add_output_file(output_file)
        pipeline_state.file_metadata[str(test_file)] = file_metadata
        
        # Process file
        await split_phase.process_file(test_file, pipeline_state.output_dir)
        
        # Verify metadata updates
        assert file_metadata.metadata.get("section_count", 0) == 2
        assert file_metadata.metadata.get("phase_status", {}).get("split") == "completed"
        assert file_metadata.processed
        assert not file_metadata.has_errors 