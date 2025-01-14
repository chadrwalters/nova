"""Tests for process notes command."""
import logging
from datetime import datetime
from typing import Any
import pytest
import click
from pathlib import Path

from nova.stubs.docling import InputFormat
from nova.cli.commands.process_notes import ProcessNotesCommand

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def setup_logging(caplog: pytest.LogCaptureFixture) -> None:
    """Set up logging for tests."""
    caplog.set_level(logging.DEBUG)
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger("nova").setLevel(logging.DEBUG)


@pytest.fixture
def mock_config(tmp_path: Path) -> dict[str, Path]:
    """Create mock config for testing."""
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)

    # Create test note files
    test_txt = input_dir / "test.txt"
    test_txt.write_text("Test note content")
    test_md = input_dir / "test.md"
    test_md.write_text("# Test markdown content")

    return {"input_dir": input_dir, "output_dir": output_dir}


@pytest.fixture
def mock_parser(monkeypatch: pytest.MonkeyPatch) -> None:
    """Create mock parser for testing."""

    class MockDocument:
        """Mock document class."""

        def __init__(self, name: str) -> None:
            """Initialize document."""
            self.name = name
            self.text = ""
            self.metadata: dict[str, Any] = {
                "title": name,
                "date": datetime.now().isoformat(),
                "tags": [],
                "format": "md",
            }
            self.pictures: list[Any] = []

    class MockDocumentConverter:
        """Mock document converter class."""

        def __init__(self, allowed_formats: list[InputFormat] | None = None) -> None:
            """Initialize converter."""
            self.input_dir = ""
            self.allowed_formats = allowed_formats or [InputFormat.MD]

        def _create_document(self, path: Path) -> MockDocument:
            """Create a document from a file."""
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")

            logger.debug("Creating document for %s", path)
            doc = MockDocument(path.stem)
            doc.text = path.read_text()
            doc.metadata = {
                "title": path.stem,
                "date": datetime.now().isoformat(),
                "tags": [],
                "format": path.suffix.lstrip("."),
            }
            logger.debug("Created document: %s", doc.metadata)
            return doc

        def convert_all(self, paths: list[Path]) -> list[MockDocument]:
            """Convert all files to documents."""
            if not paths:
                logger.warning("No note files found in %s", self.input_dir)
                return []

            # Set input_dir from first path's parent
            if paths:
                self.input_dir = str(paths[0].parent)
            logger.debug("Converting files in %s: %s", self.input_dir, paths)

            results = []
            for note_file in paths:
                try:
                    doc = self._create_document(note_file)
                    results.append(doc)  # Add document to results
                    logger.debug("Processed note file %s", note_file)
                except Exception as e:
                    logger.error("Failed to process note file %s: %s", note_file, e)
                    continue

            return results

        def convert_file(self, path: Path) -> MockDocument:
            """Convert a file to a document."""
            if path.name == "nonexistent.md":
                raise FileNotFoundError(f"File not found: {path}")
            logger.debug("Converting file: %s", path)
            doc = self._create_document(path)
            logger.debug("Converted file to document: %s", doc.metadata)
            return doc

    # Mock the docling classes
    monkeypatch.setattr("nova.stubs.docling.Document", MockDocument)
    monkeypatch.setattr("nova.stubs.docling.DocumentConverter", MockDocumentConverter)


def test_process_notes_default_paths(
    mock_config: dict[str, Path], mock_parser: None, caplog: pytest.LogCaptureFixture
) -> None:
    """Test process notes command with default paths."""
    command = ProcessNotesCommand()
    command.run(
        input_dir=mock_config["input_dir"],
        output_dir=mock_config["output_dir"],
    )
    assert "Processing notes from" in caplog.text
    assert "Processed 2 notes" in caplog.text  # Updated to expect 2 notes

    # Check that both files were processed
    output_files = list(mock_config["output_dir"].glob("*.md"))
    assert len(output_files) == 2, f"Expected 2 output files, got {len(output_files)}"
    assert any(
        f.name == "test_md.md" for f in output_files
    ), "test_md.md not found in output"
    assert any(
        f.name == "test_txt.md" for f in output_files
    ), "test_txt.md not found in output"


def test_process_notes_custom_paths(
    mock_config: dict[str, Path], mock_parser: None, caplog: pytest.LogCaptureFixture
) -> None:
    """Test process notes command with custom paths."""
    command = ProcessNotesCommand()
    command.run(
        input_dir=mock_config["input_dir"],
        output_dir=mock_config["output_dir"],
    )
    assert "Processing notes from" in caplog.text
    assert "Processed 2 notes" in caplog.text  # Updated to expect 2 notes

    # Check that both files were processed
    output_files = list(mock_config["output_dir"].glob("*.md"))
    assert len(output_files) == 2, f"Expected 2 output files, got {len(output_files)}"
    assert any(
        f.name == "test_md.md" for f in output_files
    ), "test_md.md not found in output"
    assert any(
        f.name == "test_txt.md" for f in output_files
    ), "test_txt.md not found in output"


def test_process_notes_parser_error(
    mock_config: dict[str, Path], mock_parser: None, caplog: pytest.LogCaptureFixture
) -> None:
    """Test process notes command with parser error."""
    command = ProcessNotesCommand()
    error_dir = mock_config["input_dir"] / "error"
    error_dir.mkdir(exist_ok=True)

    with pytest.raises(click.ClickException):
        command.run(
            input_dir=error_dir,
            output_dir=mock_config["output_dir"],
        )
    assert "Failed to process notes: Parser error" in caplog.text
