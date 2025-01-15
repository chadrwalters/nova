"""Tests for process notes command."""
import logging
from datetime import datetime
from typing import Any
import pytest
import click
from pathlib import Path
from click.testing import CliRunner
import shutil
import tempfile

from nova.stubs.docling import Document, DocumentConverter, InputFormat
from nova.cli.commands.process_notes import ProcessNotesCommand
from nova.cli.utils.command import NovaCommand

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
    """Mock the docling classes."""

    class MockDocumentConverter(DocumentConverter):
        """Mock document converter class."""

        def __init__(self) -> None:
            """Initialize converter."""
            allowed_formats = [InputFormat.MD, InputFormat.HTML, InputFormat.PDF, InputFormat.ASCIIDOC]
            super().__init__(allowed_formats=allowed_formats)
            self.input_dir = ""

        def _create_document(self, path: Path) -> Document:
            """Create a document from a file."""
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")

            logger.debug("Creating document for %s", path)
            doc = Document(path.stem)
            doc.text = path.read_text()
            doc.metadata = {
                "title": path.stem,
                "date": datetime.now().isoformat(),
                "tags": [],
                "format": path.suffix.lstrip("."),
            }
            logger.debug("Created document: %s", doc.metadata)
            return doc

        def convert_all(self, paths: list[Path]) -> list[Document]:
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

        def convert_file(self, path: Path) -> Document:
            """Convert a file to a document."""
            if path.name == "nonexistent.md":
                raise FileNotFoundError(f"File not found: {path}")
            logger.debug("Converting file: %s", path)
            return self._create_document(path)

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


def test_format_detection(tmp_path: Path) -> None:
    """Test format detection for different file types."""
    # Create test files
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    # Create test files with different formats
    (input_dir / "test.md").write_text("# Test Markdown")
    (input_dir / "test.txt").write_text("Plain text")
    (input_dir / "test.html").write_text("<h1>Test HTML</h1>")

    runner = CliRunner()
    cmd = ProcessNotesCommand()

    result = runner.invoke(cmd.create_command(), ["--input-dir", str(input_dir)])
    assert result.exit_code == 0
    assert "Detected formats" in result.output
    assert "markdown" in result.output.lower()
    assert "text" in result.output.lower()
    assert "html" in result.output.lower()


def test_format_conversion(tmp_path: Path) -> None:
    """Test format conversion for supported types."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    # Create test files that need conversion
    (input_dir / "test.html").write_text("<h1>Test HTML</h1><p>Content</p>")
    (input_dir / "test.rst").write_text("Test RST\n=======\n\nContent")

    runner = CliRunner()
    cmd = ProcessNotesCommand()

    result = runner.invoke(cmd.create_command(), ["--input-dir", str(input_dir)])
    assert result.exit_code == 0
    assert "Converting formats" in result.output
    assert "html -> markdown" in result.output.lower()
    assert "rst -> markdown" in result.output.lower()


def test_validation_errors(tmp_path: Path) -> None:
    """Test handling of validation errors."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    # Create an invalid file
    (input_dir / "test.bin").write_bytes(b"\x00\x01\x02")

    runner = CliRunner()
    cmd = ProcessNotesCommand()

    result = runner.invoke(cmd.create_command(), ["--input-dir", str(input_dir)])
    assert result.exit_code == 1
    assert "Validation error" in result.output
    assert "Unsupported format" in result.output


def test_progress_reporting(tmp_path: Path) -> None:
    """Test progress reporting during processing."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    # Create multiple test files
    for i in range(5):
        (input_dir / f"test{i}.md").write_text(f"# Test {i}")

    runner = CliRunner()
    cmd = ProcessNotesCommand()

    result = runner.invoke(cmd.create_command(), ["--input-dir", str(input_dir)])
    assert result.exit_code == 0
    assert "Processing files" in result.output
    assert "Progress:" in result.output
    assert "100%" in result.output
