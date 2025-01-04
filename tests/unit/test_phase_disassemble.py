"""
Unit tests for Nova disassemble phase.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
from nova.phases.disassemble import DisassemblyPhase
from nova.core.metadata import FileMetadata
from nova.config.settings import NovaConfig, CacheConfig, APIConfig, OpenAIConfig


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
def mock_pipeline(mock_fs, nova_config):
    """Create a mock pipeline."""
    pipeline = MagicMock()
    pipeline.name = "test"
    pipeline.state = {
        "disassemble": {
            "successful_files": set(),
            "failed_files": set(),
            "skipped_files": set(),
            "unchanged_files": set(),
            "reprocessed_files": set(),
            "attachments": {},
            "_file_errors": {},
            "stats": {
                "summary_files": {"created": 0, "empty": 0, "failed": 0},
                "raw_notes_files": {"created": 0, "empty": 0, "failed": 0},
                "attachments": {"copied": 0, "failed": 0},
                "total_sections": 0,
                "total_processed": 0,
                "total_attachments": 0,
                "total_outputs": 0
            }
        }
    }
    pipeline.output_manager = MagicMock()
    pipeline.output_manager.get_output_path_for_phase.return_value = mock_fs["output"] / "test.md"
    pipeline.config = nova_config
    pipeline.get_phase_output_dir.return_value = mock_fs["output"]
    return pipeline


@pytest.fixture
def test_state(nova_config, mock_pipeline):
    """Create test state."""
    return {
        "skipped_files": set(),
        "processed_files": set(),
        "errors": [],
        "metrics": {},
        "config": nova_config,
        "pipeline": mock_pipeline
    }


@pytest.fixture
def parse_dir(mock_fs):
    """Create and return the parse phase directory."""
    parse_dir = mock_fs["processing"] / "phases" / "parse"
    parse_dir.mkdir(parents=True, exist_ok=True)
    return parse_dir


@pytest.mark.unit
@pytest.mark.phases
@pytest.mark.asyncio
class TestDisassemblePhase:
    """Test disassemble phase functionality."""
    
    async def test_basic_disassembly(self, mock_fs, test_state, parse_dir):
        """Test basic document disassembly."""
        # Create test parsed markdown file
        test_file = parse_dir / "test.parsed.md"
        test_content = """# Test Document
This is the summary section.

Some more summary content.

--==RAW NOTES==--

These are raw notes.
- Note item 1
- Note item 2"""
        
        test_file.write_text(test_content)
        
        # Set up disassemble phase
        phase = DisassemblyPhase(test_state["config"], test_state["pipeline"])
        
        # Process the file
        result = await phase.process_impl(test_file, mock_fs["output"])
        
        # Verify results
        assert result is not None
        assert result.processed is True
        assert len(result.output_files) == 2  # Should have summary and raw notes
        
        # Check output files
        summary_file = mock_fs["output"] / "test.summary.md"
        raw_notes_file = mock_fs["output"] / "test.rawnotes.md"
        
        assert summary_file.exists()
        assert raw_notes_file.exists()
        
        # Verify content
        summary_content = summary_file.read_text()
        raw_notes_content = raw_notes_file.read_text()
        
        assert "# Test Document" in summary_content
        assert "This is the summary section." in summary_content
        assert "Some more summary content." in summary_content
        assert "--==RAW NOTES==--" not in summary_content
        
        assert "These are raw notes." in raw_notes_content
        assert "- Note item 1" in raw_notes_content
        assert "- Note item 2" in raw_notes_content
        assert "--==RAW NOTES==--" not in raw_notes_content
        
        # Verify pipeline state
        assert test_file in phase.pipeline.state["disassemble"]["successful_files"]
        assert phase.pipeline.state["disassemble"]["stats"]["total_sections"] == 2
        assert phase.pipeline.state["disassemble"]["stats"]["summary_files"]["created"] == 1
        assert phase.pipeline.state["disassemble"]["stats"]["raw_notes_files"]["created"] == 1
    
    async def test_no_explicit_sections(self, mock_fs, test_state, parse_dir):
        """Test handling documents without explicit sections."""
        # Create test parsed markdown file without section marker
        test_file = parse_dir / "test.parsed.md"
        test_content = """# Test Document
This is a document without explicit sections.

It should all be treated as summary content.

- List item 1
- List item 2

## Another heading
More content here."""
        
        test_file.write_text(test_content)
        
        # Set up disassemble phase
        phase = DisassemblyPhase(test_state["config"], test_state["pipeline"])
        
        # Process the file
        result = await phase.process_impl(test_file, mock_fs["output"])
        
        # Verify results
        assert result is not None
        assert result.processed is True
        assert len(result.output_files) == 1  # Should only have summary file
        
        # Check output files
        summary_file = mock_fs["output"] / "test.summary.md"
        raw_notes_file = mock_fs["output"] / "test.rawnotes.md"
        
        assert summary_file.exists()
        assert not raw_notes_file.exists()  # Raw notes file should not exist
        
        # Verify content
        summary_content = summary_file.read_text()
        
        assert "# Test Document" in summary_content
        assert "This is a document without explicit sections." in summary_content
        assert "It should all be treated as summary content." in summary_content
        assert "- List item 1" in summary_content
        assert "- List item 2" in summary_content
        assert "## Another heading" in summary_content
        assert "More content here." in summary_content
        
        # Verify pipeline state
        assert test_file in phase.pipeline.state["disassemble"]["successful_files"]
        assert phase.pipeline.state["disassemble"]["stats"]["total_sections"] == 1
        assert phase.pipeline.state["disassemble"]["stats"]["summary_files"]["created"] == 1
        assert phase.pipeline.state["disassemble"]["stats"]["raw_notes_files"]["empty"] == 1
    
    async def test_nested_sections(self, mock_fs, test_state, parse_dir):
        """Test handling nested document sections."""
        # Create test parsed markdown file with nested sections
        test_file = parse_dir / "test.parsed.md"
        test_content = """# Main Document
## Section 1
Content for section 1.

### Subsection 1.1
Nested content 1.1.

### Subsection 1.2
Nested content 1.2.

## Section 2
Content for section 2.

--==RAW NOTES==--

# Raw Notes Main
## Raw Notes Section 1
Raw notes content 1.

### Raw Notes Subsection 1.1
Nested raw notes 1.1.

## Raw Notes Section 2
Raw notes content 2."""
        
        test_file.write_text(test_content)
        
        # Set up disassemble phase
        phase = DisassemblyPhase(test_state["config"], test_state["pipeline"])
        
        # Process the file
        result = await phase.process_impl(test_file, mock_fs["output"])
        
        # Verify results
        assert result is not None
        assert result.processed is True
        assert len(result.output_files) == 2  # Should have summary and raw notes
        
        # Check output files
        summary_file = mock_fs["output"] / "test.summary.md"
        raw_notes_file = mock_fs["output"] / "test.rawnotes.md"
        
        assert summary_file.exists()
        assert raw_notes_file.exists()
        
        # Verify summary content and structure
        summary_content = summary_file.read_text()
        assert "# Main Document" in summary_content
        assert "## Section 1" in summary_content
        assert "### Subsection 1.1" in summary_content
        assert "### Subsection 1.2" in summary_content
        assert "## Section 2" in summary_content
        assert "Content for section 1." in summary_content
        assert "Nested content 1.1." in summary_content
        assert "Nested content 1.2." in summary_content
        assert "Content for section 2." in summary_content
        assert "--==RAW NOTES==--" not in summary_content
        
        # Verify raw notes content and structure
        raw_notes_content = raw_notes_file.read_text()
        assert "# Raw Notes Main" in raw_notes_content
        assert "## Raw Notes Section 1" in raw_notes_content
        assert "### Raw Notes Subsection 1.1" in raw_notes_content
        assert "## Raw Notes Section 2" in raw_notes_content
        assert "Raw notes content 1." in raw_notes_content
        assert "Nested raw notes 1.1." in raw_notes_content
        assert "Raw notes content 2." in raw_notes_content
        assert "--==RAW NOTES==--" not in raw_notes_content
        
        # Verify pipeline state
        assert test_file in phase.pipeline.state["disassemble"]["successful_files"]
        assert phase.pipeline.state["disassemble"]["stats"]["total_sections"] == 2
        assert phase.pipeline.state["disassemble"]["stats"]["summary_files"]["created"] == 1
        assert phase.pipeline.state["disassemble"]["stats"]["raw_notes_files"]["created"] == 1
    
    async def test_code_block_preservation(self, mock_fs, test_state, parse_dir):
        """Test preservation of code blocks during disassembly."""
        # Create test parsed markdown file with code blocks
        test_file = parse_dir / "test.parsed.md"
        test_content = """# Code Examples

## Python Example
Here's a Python code block:

```python
def hello_world():
    print("Hello, World!")
    
    # Indented comment
    for i in range(3):
        print(f"Count: {i}")
```

## JavaScript Example
And here's some JavaScript:

```javascript
function calculateSum(a, b) {
    // Add two numbers
    return a + b;
}

// Call the function
console.log(calculateSum(5, 3));
```

--==RAW NOTES==--

## Implementation Notes

Here's the test code:

```python
def test_hello_world():
    # Arrange
    expected = "Hello, World!"
    
    # Act
    result = hello_world()
    
    # Assert
    assert result == expected
```

And some shell commands:

```bash
# Build the project
npm install
npm run build

# Run tests
pytest tests/
```"""
        
        test_file.write_text(test_content)
        
        # Set up disassemble phase
        phase = DisassemblyPhase(test_state["config"], test_state["pipeline"])
        
        # Process the file
        result = await phase.process_impl(test_file, mock_fs["output"])
        
        # Verify results
        assert result is not None
        assert result.processed is True
        assert len(result.output_files) == 2  # Should have summary and raw notes
        
        # Check output files
        summary_file = mock_fs["output"] / "test.summary.md"
        raw_notes_file = mock_fs["output"] / "test.rawnotes.md"
        
        assert summary_file.exists()
        assert raw_notes_file.exists()
        
        # Verify summary content
        summary_content = summary_file.read_text()
        
        # Check Python code block
        assert "```python" in summary_content
        assert "def hello_world():" in summary_content
        assert "    print(\"Hello, World!\")" in summary_content
        assert "    # Indented comment" in summary_content
        assert "    for i in range(3):" in summary_content
        assert "        print(f\"Count: {i}\")" in summary_content
        assert "```" in summary_content
        
        # Check JavaScript code block
        assert "```javascript" in summary_content
        assert "function calculateSum(a, b) {" in summary_content
        assert "    // Add two numbers" in summary_content
        assert "    return a + b;" in summary_content
        assert "console.log(calculateSum(5, 3));" in summary_content
        
        # Verify raw notes content
        raw_notes_content = raw_notes_file.read_text()
        
        # Check Python test code block
        assert "```python" in raw_notes_content
        assert "def test_hello_world():" in raw_notes_content
        assert "    # Arrange" in raw_notes_content
        assert "    expected = \"Hello, World!\"" in raw_notes_content
        assert "    # Assert" in raw_notes_content
        assert "    assert result == expected" in raw_notes_content
        
        # Check bash code block
        assert "```bash" in raw_notes_content
        assert "# Build the project" in raw_notes_content
        assert "npm install" in raw_notes_content
        assert "npm run build" in raw_notes_content
        assert "# Run tests" in raw_notes_content
        assert "pytest tests/" in raw_notes_content
        
        # Verify no section markers in output
        assert "--==RAW NOTES==--" not in summary_content
        assert "--==RAW NOTES==--" not in raw_notes_content
        
        # Verify pipeline state
        assert test_file in phase.pipeline.state["disassemble"]["successful_files"]
        assert phase.pipeline.state["disassemble"]["stats"]["total_sections"] == 2
        assert phase.pipeline.state["disassemble"]["stats"]["summary_files"]["created"] == 1
        assert phase.pipeline.state["disassemble"]["stats"]["raw_notes_files"]["created"] == 1
    
    async def test_metadata_updates(self, mock_fs, test_state, parse_dir):
        """Test metadata updates during disassembly."""
        # Create test parsed markdown file
        test_file = parse_dir / "test.parsed.md"
        test_content = """# Test Document
Summary content here.

--==RAW NOTES==--

Raw notes content here."""
        
        test_file.write_text(test_content)
        
        # Create test attachment files
        attachments_dir = parse_dir / "test"
        attachments_dir.mkdir(parents=True)
        
        # Create various attachment types
        (attachments_dir / "image.png").write_bytes(b"fake png data")
        (attachments_dir / "doc.pdf").write_bytes(b"fake pdf data")
        (attachments_dir / "data.json").write_text('{"key": "value"}')
        
        # Create initial metadata
        metadata = FileMetadata.from_file(
            file_path=test_file,
            handler_name="disassemble",
            handler_version="1.0"
        )
        metadata.title = "Test Document"
        metadata.tags = ["test", "metadata"]
        
        # Set up disassemble phase
        phase = DisassemblyPhase(test_state["config"], test_state["pipeline"])
        
        # Process the file with metadata
        result = await phase.process_impl(test_file, mock_fs["output"], metadata)
        
        # Verify results
        assert result is not None
        assert result.processed is True
        assert len(result.output_files) == 2  # Should have summary and raw notes
        
        # Verify metadata preservation
        assert result.title == "Test Document"
        assert result.tags == ["test", "metadata"]
        
        # Verify attachment handling in metadata
        assert "attachments" in phase.pipeline.state["disassemble"]
        attachments = phase.pipeline.state["disassemble"]["attachments"].get("test", [])
        assert len(attachments) == 3  # Should have all three attachments
        
        # Verify attachment types
        attachment_types = {att["type"] for att in attachments}
        assert "IMAGE" in attachment_types
        assert "PDF" in attachment_types
        assert "JSON" in attachment_types
        
        # Verify pipeline state and stats
        assert test_file in phase.pipeline.state["disassemble"]["successful_files"]
        assert phase.pipeline.state["disassemble"]["stats"]["total_sections"] == 2
        assert phase.pipeline.state["disassemble"]["stats"]["summary_files"]["created"] == 1
        assert phase.pipeline.state["disassemble"]["stats"]["raw_notes_files"]["created"] == 1
        assert phase.pipeline.state["disassemble"]["stats"]["attachments"]["copied"] == 3
        assert phase.pipeline.state["disassemble"]["stats"]["total_attachments"] == 3
        
        # Verify error tracking
        assert not hasattr(result, "errors") or not result.errors
        assert test_file not in phase.pipeline.state["disassemble"].get("failed_files", set())
        assert test_file not in phase.pipeline.state["disassemble"].get("_file_errors", {}) 