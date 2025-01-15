"""Unit tests for note resource handler."""

from pathlib import Path
from datetime import datetime
import copy

import pytest
from fastapi import HTTPException
from nova.stubs.docling import Document, DocumentConverter, InputFormat

from nova.server.resources.note import NoteHandler
from nova.server.types import ResourceType
from tests.unit.test_fixtures import DocumentFixtures
from tests.unit.test_data_generators import TestDataGenerators


class MockDocumentConverter(DocumentConverter):
    """Mock document converter for testing."""

    def __init__(self) -> None:
        """Initialize mock converter."""
        super().__init__()
        self._documents: dict[str, Document] = {}
        self._allowed_formats = {InputFormat.MD, InputFormat.HTML, InputFormat.ASCIIDOC}

    def convert_file(self, path: Path) -> Document:
        """Convert a file to a document."""
        # For list_notes, return a listing document
        if str(path) == ".nova/test_input":
            listing = Document("listing.md")
            listing.metadata["documents"] = list(self._documents.values())
            return listing

        if path.name not in self._documents:
            raise FileNotFoundError(f"File not found: {path}")

        return copy.deepcopy(self._documents[path.name])

    def add_document(self, doc: Document) -> None:
        """Add a document to the mock store."""
        self._documents[doc.name] = copy.deepcopy(doc)

    def convert_all(self, paths: list[Path]) -> list[Document]:
        """Convert multiple files to documents."""
        return [self.convert_file(path) for path in paths]


class RandomDocConverter(DocumentConverter):
    """Random document converter for testing."""

    def __init__(self, documents: list[Document]) -> None:
        """Initialize random document converter."""
        super().__init__()
        self._documents = {doc.name: doc for doc in documents}
        self._allowed_formats = {InputFormat.MD, InputFormat.HTML, InputFormat.ASCIIDOC}

    def convert_file(self, path: Path) -> Document:
        """Convert a file to a document."""
        # For list_notes, return a listing document
        if str(path) == ".nova/test_input":
            listing = Document("listing.md")
            listing.metadata["documents"] = list(self._documents.values())
            return listing

        if path.name not in self._documents:
            raise FileNotFoundError(f"File not found: {path}")

        return copy.deepcopy(self._documents[path.name])

    def convert_all(self, paths: list[Path]) -> list[Document]:
        """Convert multiple files to documents."""
        return [self.convert_file(path) for path in paths]

    @property
    def allowed_formats(self) -> list[InputFormat]:
        """Get allowed formats."""
        return [InputFormat.MD, InputFormat.HTML, InputFormat.ASCIIDOC]


@pytest.fixture
def notes_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for notes."""
    notes = tmp_path / "notes"
    notes.mkdir(exist_ok=True)

    # Create test files
    for name in ["test1.md", "test2.md", "test3.md"]:
        test_file = notes / name
        test_file.write_text(f"Test content for {name}")

    return notes


@pytest.fixture
def note_handler(notes_dir: Path) -> NoteHandler:
    """Create a note handler for testing."""
    converter = MockDocumentConverter()

    # Create test documents
    docs = [
        Document("test1.md"),
        Document("test2.md"),
        Document("test3.md"),
    ]

    now = datetime.now().isoformat()

    # Set up test1.md
    docs[0].text = "# Test Document\nThis is a test document in markdown format"
    docs[0].metadata = {
        "title": "Test Note 1",
        "format": InputFormat.MD,
        "tags": ["tag1", "tag2"],
        "created": now,
        "modified": now,
        "date": now,
        "size": len(docs[0].text),
        "pictures": [],
    }

    # Set up test2.md
    docs[1].text = "# Test Document 2\nTest content with metadata"
    docs[1].metadata = {
        "title": "Test Note 2",
        "format": InputFormat.MD,
        "tags": ["tag2", "tag3"],
        "created": now,
        "modified": now,
        "date": now,
        "size": len(docs[1].text),
        "pictures": [],
    }

    # Set up test3.md
    docs[2].text = "# Test Document 3\nTest content with attachments"
    docs[2].metadata = {
        "title": "Test Note 3",
        "format": InputFormat.MD,
        "tags": ["tag3", "tag4"],
        "created": now,
        "modified": now,
        "date": now,
        "size": len(docs[2].text),
        "pictures": [],
    }

    # Add documents to converter
    for doc in docs:
        converter._documents[doc.name] = doc

    # Create listing document
    listing = Document("listing.md")
    listing.metadata = {
        "format": InputFormat.MD,
        "documents": docs,
        "created": now,
        "modified": now,
        "date": now,
        "title": "Document Listing",
        "tags": [],
        "pictures": [],
        "size": 0,
    }
    converter._documents[".nova/test_input"] = listing

    return NoteHandler(converter)


def test_init_handler(notes_dir: Path) -> None:
    """Test initializing the handler."""
    converter = MockDocumentConverter()
    handler = NoteHandler(converter)
    assert handler is not None


def test_get_note_metadata(note_handler: NoteHandler) -> None:
    """Test getting note metadata."""
    metadata = note_handler.get_metadata()
    assert metadata["type"] == ResourceType.NOTE
    assert metadata["version"] == "1.0.0"


def test_get_note_content(note_handler: NoteHandler) -> None:
    """Test getting note content."""
    content = note_handler.get_note_content("test1.md")
    assert "# Test Document" in content
    assert "test document in markdown format" in content


def test_list_notes(note_handler: NoteHandler) -> None:
    """Test listing notes."""
    notes = note_handler.list_notes()
    assert len(notes) == 4  # test1.md, test2.md, test3.md, listing.md
    assert all(note["type"] == ResourceType.NOTE for note in notes)
    assert all("title" in note["metadata"] for note in notes)
    assert all("date" in note["metadata"] for note in notes)
    assert all("format" in note["metadata"] for note in notes)
    assert all("modified" in note["metadata"] for note in notes)
    assert all("size" in note["metadata"] for note in notes)


def test_validate_access(note_handler: NoteHandler) -> None:
    """Test validating note access."""
    with pytest.raises(HTTPException) as exc_info:
        note_handler.get_note_content("nonexistent.md")
    assert exc_info.value.status_code == 404


def test_document_format_validation(note_handler: NoteHandler) -> None:
    """Test document format validation."""
    notes = note_handler.list_notes()
    for note in notes:
        assert "format" in note["metadata"]


def test_document_metadata_validation(note_handler: NoteHandler) -> None:
    """Test document metadata validation."""
    notes = note_handler.list_notes()
    for note in notes:
        # Required fields
        assert "title" in note["metadata"]
        assert "date" in note["metadata"]
        assert "format" in note["metadata"]
        assert "modified" in note["metadata"]
        assert "size" in note["metadata"]

        # Date format validation
        for date_field in ["date", "modified"]:
            try:
                datetime.fromisoformat(note["metadata"][date_field])
            except ValueError:
                pytest.fail(f"Invalid date format for {date_field}")

        # Validate format
        assert note["metadata"]["format"] in [f.value for f in InputFormat]

        # Validate tags
        assert "tags" in note["metadata"]
        assert isinstance(note["metadata"]["tags"], list)
        assert all(isinstance(tag, str) for tag in note["metadata"]["tags"])


def test_document_content_validation(note_handler: NoteHandler) -> None:
    """Test document content validation."""
    for name in ["test1.md", "test2.md", "test3.md"]:
        content = note_handler.get_note_content(name)
        assert content is not None
        assert len(content) > 0
        assert isinstance(content, str)


def test_cleanup(note_handler: NoteHandler) -> None:
    """Test cleanup."""
    note_handler.cleanup()


def test_on_change(note_handler: NoteHandler) -> None:
    """Test change notification."""
    def callback() -> None:
        pass
    note_handler.on_change(callback)


def test_random_document_handling(notes_dir: Path) -> None:
    """Test handling of randomly generated documents."""
    # Generate random documents
    random_docs = TestDataGenerators.generate_document_batch(
        num_documents=5,
        formats=[InputFormat.MD, InputFormat.HTML, InputFormat.ASCIIDOC],
        with_metadata=True,
        with_images=True,
    )

    # Create converter with random documents
    converter = RandomDocConverter(random_docs)
    handler = NoteHandler(converter)

    # Test listing
    notes = handler.list_notes()
    assert len(notes) == 5

    # Validate each note
    for note in notes:
        # Basic validation
        assert "name" in note
        assert "title" in note
        assert "format" in note
        assert note["format"] in [f.value for f in InputFormat]

        # Content validation
        content = handler.get_note_content(note["name"])
        assert content is not None
        assert len(content) > 0

        # Metadata validation
        assert "metadata" in note
        assert "author" in note["metadata"]
        assert "category" in note["metadata"]
        assert "status" in note["metadata"]
        assert "version" in note["metadata"]
        assert "priority" in note["metadata"]

        # Image validation if present
        if "pictures" in note and note["pictures"]:
            for picture in note["pictures"]:
                assert "image" in picture
                assert "uri" in picture["image"]
                assert "mime_type" in picture["image"]
                assert "size" in picture["image"]
                assert "width" in picture["image"]
                assert "height" in picture["image"]
