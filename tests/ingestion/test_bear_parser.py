"""Tests for the Bear parser."""
import os
import tempfile
from pathlib import Path
from collections.abc import Generator
import pytest
from pytest import FixtureRequest
from nova.bear_parser.parser import BearParser, BearAttachment


@pytest.fixture(scope="function")
def note_dir(_request: FixtureRequest) -> Generator[Path, None, None]:
    """Create a temporary directory for test notes."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture(scope="function")
def nova_dir(_request: FixtureRequest) -> Generator[Path, None, None]:
    """Create a temporary directory for Nova files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        nova_dir = Path(temp_dir) / ".nova"
        nova_dir.mkdir()
        yield nova_dir


@pytest.fixture(scope="function")
def test_note(note_dir: Path, _request: FixtureRequest) -> Generator[Path, None, None]:
    """Create a test note file."""
    note_content = """# Test Note

This is a test note with some content.

#tag1 #tag2

And here's an image:
![Test Image](assets/test_image.png)

## Section 1

Some content in section 1.

## Section 2

Some content in section 2."""

    # Create note file
    note_file = note_dir / "test_note.md"
    note_file.write_text(note_content)

    # Create assets directory and test image
    assets_dir = note_dir / "assets"
    assets_dir.mkdir()
    image_file = assets_dir / "test_image.png"
    image_file.write_bytes(b"test image data")

    yield note_file


@pytest.mark.asyncio
async def test_parse_note(note_dir: Path, nova_dir: Path, test_note: Path) -> None:
    """Test parsing a single note."""
    parser = BearParser(notes_dir=note_dir)
    note = await parser.parse_note(test_note)

    assert note.title == "Test Note"
    assert note.content.startswith("# Test Note")
    assert note.tags == {"tag1", "tag2"}
    assert len(note.attachments) == 1
    assert isinstance(note.attachments[0], BearAttachment)
    assert note.attachments[0].path == Path("assets/test_image.png")


@pytest.mark.asyncio
async def test_parse_directory(note_dir: Path, nova_dir: Path) -> None:
    """Test parsing a directory of notes."""
    parser = BearParser(notes_dir=note_dir)
    notes = await parser.parse_directory()

    assert len(notes) == 1
    assert notes[0].title == "Test Note"


@pytest.mark.asyncio
async def test_attachment_processing(
    note_dir: Path, nova_dir: Path, test_note: Path
) -> None:
    """Test processing of attachments."""
    parser = BearParser(notes_dir=note_dir)
    note = await parser.parse_note(test_note)

    # Check attachment was processed
    attachment = note.attachments[0]
    assert isinstance(attachment, BearAttachment)
    assert attachment.path == Path("assets/test_image.png")
    assert os.path.exists(nova_dir / "attachments" / attachment.path.name)


@pytest.mark.asyncio
async def test_placeholder_generation(
    note_dir: Path, nova_dir: Path, test_note: Path
) -> None:
    """Test generation of placeholders for attachments."""
    parser = BearParser(notes_dir=note_dir)
    note = await parser.parse_note(test_note)

    # Check placeholder was generated
    attachment = note.attachments[0]
    assert isinstance(attachment, BearAttachment)
    assert attachment.path == Path("assets/test_image.png")
    assert f"![Test Image]({attachment.path})" in note.content
