"""Tests for process notes command."""
import logging
import pytest
import click
from pathlib import Path

from nova.cli.commands.process_notes import ProcessNotesCommand

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def setup_logging(caplog: pytest.LogCaptureFixture) -> None:
    """Set up logging for tests."""
    caplog.set_level(logging.INFO)


@pytest.fixture
def mock_config(tmp_path: Path) -> dict[str, Path]:
    """Create mock config for testing."""
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)

    # Create test note files
    test_note = input_dir / "test.txt"
    test_note.write_text("Test note content")

    return {"input_dir": input_dir, "output_dir": output_dir}


@pytest.fixture
def mock_parser(monkeypatch: pytest.MonkeyPatch) -> None:
    """Create mock parser for testing."""

    def mock_process_note(note_file: Path, output_dir: Path) -> list[str]:
        if "error" in str(note_file):
            raise Exception("Parser error")
        return ["Test content"]

    class MockBearParser:
        def __init__(self) -> None:
            pass

        def process_notes(self, input_dir: str, output_dir: str) -> None:
            input_path = Path(input_dir)
            output_path = Path(output_dir)

            note_files = list(input_path.glob("*.txt"))
            if not note_files:
                logger.warning("No note files found in %s", input_dir)
                return

            for note_file in note_files:
                try:
                    mock_process_note(note_file, output_path)
                    logger.info("Processed note: %s", note_file.name)
                except Exception as e:
                    logger.error("Failed to process note %s: %s", note_file.name, e)
                    raise

    monkeypatch.setattr("nova.ingestion.bear.BearParser", MockBearParser)
    monkeypatch.setattr("nova.ingestion.bear.process_note", mock_process_note)


def test_process_notes_default_paths(
    mock_config: dict[str, Path], mock_parser: None, caplog: pytest.LogCaptureFixture
) -> None:
    """Test process notes command with default paths."""
    command = ProcessNotesCommand()
    command.run(input_dir=str(mock_config["input_dir"]))
    assert "Processing notes from" in caplog.text


def test_process_notes_custom_paths(
    mock_config: dict[str, Path], mock_parser: None, caplog: pytest.LogCaptureFixture
) -> None:
    """Test process notes command with custom paths."""
    command = ProcessNotesCommand()
    command.run(
        input_dir=str(mock_config["input_dir"]),
        output_dir=str(mock_config["output_dir"]),
    )
    assert "Processing notes from" in caplog.text


def test_process_notes_parser_error(
    mock_config: dict[str, Path], mock_parser: None, caplog: pytest.LogCaptureFixture
) -> None:
    """Test process notes command with parser error."""
    command = ProcessNotesCommand()
    error_dir = mock_config["input_dir"] / "error"
    error_dir.mkdir(exist_ok=True)
    error_note = error_dir / "error.txt"
    error_note.write_text("Error note content")

    with pytest.raises(click.Abort):
        command.run(input_dir=str(error_dir))
    assert "Failed to process notes: Parser error" in caplog.text
