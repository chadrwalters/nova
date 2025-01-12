"""Tests for the process vectors command."""

import tempfile
from pathlib import Path
from collections.abc import Generator

import pytest

from nova.cli.commands.process_vectors import ProcessVectorsCommand


@pytest.fixture
def output_dir() -> Generator[Path, None, None]:
    """Create a temporary output directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


def test_process_vectors_basic(output_dir: Path) -> None:
    """Test basic vector processing."""
    command = ProcessVectorsCommand()
    text = "This is a test document."

    command.run(text=text, output_dir=str(output_dir))

    # Check that output directory exists
    assert output_dir.exists()
    assert output_dir.is_dir()


def test_process_vectors_empty_text(output_dir: Path) -> None:
    """Test processing empty text."""
    command = ProcessVectorsCommand()
    text = ""

    command.run(text=text, output_dir=str(output_dir))

    # Check that output directory exists
    assert output_dir.exists()
    assert output_dir.is_dir()


def test_process_vectors_missing_args() -> None:
    """Test missing arguments."""
    command = ProcessVectorsCommand()

    with pytest.raises(KeyError):
        command.run()

    with pytest.raises(KeyError):
        command.run(text="test")

    with pytest.raises(KeyError):
        command.run(output_dir="test")
