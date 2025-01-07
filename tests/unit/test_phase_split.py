"""
Unit tests for Nova split phase.
"""

# Standard library
from pathlib import Path
from unittest.mock import MagicMock, Mock

# External dependencies
import pytest

# Internal imports
from nova.context_processor.config.settings import NovaConfig, CacheConfig, APIConfig, OpenAIConfig
from nova.context_processor.core.metadata import DocumentMetadata
from nova.context_processor.phases.split import SplitPhase


@pytest.fixture
def nova_config(mock_fs):
    """Create test configuration."""
    config = NovaConfig(
        base_dir=str(mock_fs["root"]),
        input_dir=str(mock_fs["input"]),
        output_dir=str(mock_fs["output"]),
        processing_dir=str(mock_fs["processing"]),
        cache=CacheConfig(dir=str(mock_fs["cache"]), enabled=True, ttl=3600),
        apis=APIConfig(
            openai=OpenAIConfig(api_key="test_key", model="gpt-4o", max_tokens=300)
        ),
    )
    return config


@pytest.fixture
def mock_pipeline(mock_fs, nova_config):
    """Create a mock pipeline."""
    pipeline = MagicMock()
    pipeline.name = "test"
    pipeline.state = {
        "split": {
            "skipped_files": set(),
            "processed_files": set(),
            "errors": [],
            "stats": {
                "summary_files": {"created": 0, "empty": 0, "failed": 0},
                "raw_notes_files": {"created": 0, "empty": 0, "failed": 0},
                "attachments": {"copied": 0, "failed": 0},
                "total_sections": 0,
                "total_processed": 0,
                "total_attachments": 0,
                "total_outputs": 0,
            },
        }
    }
    pipeline.output_manager = MagicMock()
    pipeline.output_manager.get_output_path_for_phase.return_value = (
        mock_fs["output"] / "test.md"
    )
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
        "pipeline": mock_pipeline,
    }


@pytest.fixture
def disassemble_dir(mock_fs):
    """Create and return the disassemble phase directory."""
    disassemble_dir = mock_fs["processing"] / "phases" / "disassemble"
    disassemble_dir.mkdir(parents=True, exist_ok=True)
    return disassemble_dir


@pytest.mark.unit
@pytest.mark.phases
@pytest.mark.asyncio
class TestSplitPhase:
    """Test split phase functionality."""

    async def test_basic_consolidation(self, mock_fs, test_state, disassemble_dir):
        """Test basic consolidation of pre-split files."""
        # Create pre-split files in disassemble phase directory
        doc1_summary = disassemble_dir / "doc1.summary.md"
        doc1_raw = disassemble_dir / "doc1.rawnotes.md"
        doc2_summary = disassemble_dir / "doc2.summary.md"
        doc2_raw = disassemble_dir / "doc2.rawnotes.md"

        # Write test content
        doc1_summary.write_text("# Document 1\nSummary content")
        doc1_raw.write_text("Raw notes for doc 1")
        doc2_summary.write_text("# Document 2\nMore summary content")
        doc2_raw.write_text("Raw notes for doc 2")

        # Set up split phase
        phase = SplitPhase(test_state["config"], test_state["pipeline"])

        # Process the files
        for file in [doc1_summary, doc1_raw, doc2_summary, doc2_raw]:
            result = await phase.process_impl(file, mock_fs["output"])
            assert result is not None
            assert result.processed is True

        # Finalize to write out the collected sections
        phase.finalize()

        # Verify output files
        summary_file = mock_fs["output"] / "Summary.md"
        raw_notes_file = mock_fs["output"] / "Raw Notes.md"

        assert summary_file.exists()
        assert raw_notes_file.exists()

        # Verify content
        summary_content = summary_file.read_text()
        raw_notes_content = raw_notes_file.read_text()

        assert "# Document 1" in summary_content
        assert "Summary content" in summary_content
        assert "# Document 2" in summary_content
        assert "More summary content" in summary_content

        assert "Raw notes for doc 1" in raw_notes_content
        assert "Raw notes for doc 2" in raw_notes_content

    async def test_nested_sections_consolidation(
        self, mock_fs, test_state, disassemble_dir
    ):
        """Test consolidation of files with nested sections."""
        # Create pre-split files with nested sections
        doc1_summary = disassemble_dir / "doc1.summary.md"
        doc1_raw = disassemble_dir / "doc1.rawnotes.md"

        summary_content = """# Main Doc 1
## Section 1
Content 1
### Subsection 1.1
Content 1.1"""

        raw_notes_content = """## Notes Section 1
Note content 1
### Subsection Notes 1.1
Note content 1.1"""

        doc1_summary.write_text(summary_content)
        doc1_raw.write_text(raw_notes_content)

        # Set up split phase
        phase = SplitPhase(test_state["config"], test_state["pipeline"])

        # Process the files
        for file in [doc1_summary, doc1_raw]:
            result = await phase.process_impl(file, mock_fs["output"])
            assert result is not None
            assert result.processed is True

        # Finalize to write out the collected sections
        phase.finalize()

        # Verify consolidated output
        summary_file = mock_fs["output"] / "Summary.md"
        raw_notes_file = mock_fs["output"] / "Raw Notes.md"

        assert summary_file.exists()
        assert raw_notes_file.exists()

        # Check content and structure preservation
        summary_content = summary_file.read_text()
        raw_notes_content = raw_notes_file.read_text()

        # Verify section hierarchy is preserved
        assert "# Main Doc 1" in summary_content
        assert "## Section 1" in summary_content
        assert "### Subsection 1.1" in summary_content
        assert "Content 1.1" in summary_content

        assert "## Notes Section 1" in raw_notes_content
        assert "### Subsection Notes 1.1" in raw_notes_content
        assert "Note content 1.1" in raw_notes_content

    async def test_markdown_formatting_preservation(
        self, mock_fs, test_state, disassemble_dir
    ):
        """Test preservation of markdown formatting during consolidation."""
        # Create pre-split files with various markdown formatting
        doc1_summary = disassemble_dir / "doc1.summary.md"
        doc1_raw = disassemble_dir / "doc1.rawnotes.md"

        summary_content = """# Document 1
## Code Section
```python
def test():
    print("Hello")
```

## List Section
1. First item
   * Nested bullet
2. Second item
   * Another bullet
"""

        raw_notes_content = """## Raw Notes
* Bullet point
  1. Nested number
  2. Another number

```javascript
console.log("test");
```"""

        doc1_summary.write_text(summary_content)
        doc1_raw.write_text(raw_notes_content)

        # Set up split phase
        phase = SplitPhase(test_state["config"], test_state["pipeline"])

        # Process the files
        for file in [doc1_summary, doc1_raw]:
            result = await phase.process_impl(file, mock_fs["output"])
            assert result is not None
            assert result.processed is True

        # Finalize to write out the collected sections
        phase.finalize()

        # Verify consolidated output
        summary_file = mock_fs["output"] / "Summary.md"
        raw_notes_file = mock_fs["output"] / "Raw Notes.md"

        assert summary_file.exists()
        assert raw_notes_file.exists()

        # Check formatting preservation
        summary_content = summary_file.read_text()
        raw_notes_content = raw_notes_file.read_text()

        # Verify code blocks
        assert "```python" in summary_content
        assert "def test():" in summary_content
        assert "```javascript" in raw_notes_content
        assert 'console.log("test");' in raw_notes_content

        # Verify lists
        assert "1. First item" in summary_content
        assert "* Nested bullet" in summary_content
        assert "* Bullet point" in raw_notes_content
        assert "1. Nested number" in raw_notes_content

    async def test_metadata_tracking(self, mock_fs, test_state, disassemble_dir):
        """Test metadata tracking during consolidation."""
        # Create pre-split files
        doc1_summary = disassemble_dir / "doc1.summary.md"
        doc1_raw = disassemble_dir / "doc1.rawnotes.md"

        doc1_summary.write_text("# Document 1\nSummary content")
        doc1_raw.write_text("Raw notes content")

        # Create initial metadata
        metadata = DocumentMetadata.from_file(
            file_path=doc1_summary, handler_name="split", handler_version="1.0"
        )
        metadata.title = "Document 1"
        metadata.tags = ["test", "doc1"]

        # Set up split phase
        phase = SplitPhase(test_state["config"], test_state["pipeline"])

        # Process files with metadata
        result = await phase.process_impl(doc1_summary, mock_fs["output"], metadata)

        # Verify metadata preservation and updates
        assert result is not None
        assert result.processed is True
        assert result.title == "Document 1"
        assert result.tags == ["test", "doc1"]

        # Finalize to write out the collected sections
        phase.finalize()

        # Verify output files in metadata
        summary_file = mock_fs["output"] / "Summary.md"
        raw_notes_file = mock_fs["output"] / "Raw Notes.md"

        assert summary_file.exists()
        assert raw_notes_file.exists()

        # Verify content
        summary_content = summary_file.read_text()
        raw_notes_content = raw_notes_file.read_text()

        assert "# Document 1" in summary_content
        assert "Summary content" in summary_content
        assert "Raw notes content" in raw_notes_content
