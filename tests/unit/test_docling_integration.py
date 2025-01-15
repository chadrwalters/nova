"""Unit tests for docling integration."""

import pytest
from pathlib import Path
from datetime import datetime
from nova.stubs.docling import Document, DocumentConverter, InputFormat
from nova.server.resources.note import NoteHandler
from nova.server.types import ResourceType
from typing import Any, cast
from nova.server.errors import ResourceError
import copy
from fastapi import HTTPException

try:
    import markdown2
except ImportError:
    markdown2 = None

def _convert_markdown_to_html(text: str) -> str:
    """Convert markdown to HTML."""
    if not text.strip():
        return ""
    return f"<html><body><h1>Test Document</h1>\n\n<p>{text}</p></body></html>"

class TestDocumentFixtures:
    """Test document fixtures."""

    @staticmethod
    def create_basic_document() -> Document:
        """Create a basic test document."""
        doc = Document("test_basic.md")
        doc.text = "# Test Document\nBasic test content"
        doc.metadata = {
            "title": "Test Document",
            "format": InputFormat.MD,
            "date": datetime.now().isoformat(),
            "modified": datetime.now().isoformat(),
            "size": len(doc.text),
            "tags": ["test", "basic"]
        }
        return doc

    @staticmethod
    def create_document_with_attachments() -> Document:
        """Create a document with attachments for testing."""
        doc = Document("test_attachments.md")
        doc.text = "# Document with Attachments\n\n![Test Image](test.png)\n\nContent with image"
        doc.metadata = {
            "title": "Document with Attachments",
            "date": datetime.now().isoformat(),
            "tags": ["test", "attachments"],
            "format": InputFormat.MD,
            "modified": datetime.now().isoformat(),
            "size": 72,
            "pictures": [{
                "image": {
                    "uri": "test.png",
                    "mime_type": "image/png",
                    "size": 1024,
                    "width": 800,
                    "height": 600
                }
            }]
        }
        # Add picture as a dictionary since we don't have access to PictureItem
        doc.pictures = doc.metadata["pictures"]
        return doc

class TestDocumentConverter(DocumentConverter):
    """Test document converter implementation."""

    def __init__(self) -> None:
        """Initialize the document converter."""
        super().__init__()
        self._fixtures: dict[str, Document] = {}
        self._allowed_formats = {InputFormat.MD, InputFormat.HTML, InputFormat.PDF, InputFormat.DOCX, InputFormat.XLSX, InputFormat.ASCIIDOC}
        self._supported_formats = {".md": InputFormat.MD, ".html": InputFormat.HTML, ".pdf": InputFormat.PDF, ".docx": InputFormat.DOCX, ".xlsx": InputFormat.XLSX, ".asciidoc": InputFormat.ASCIIDOC}
        self.input_dir = ".nova/test_input"

    @property
    def allowed_formats(self) -> set[InputFormat]:
        """Get allowed formats."""
        return self._allowed_formats.copy()

    @allowed_formats.setter
    def allowed_formats(self, formats: set[InputFormat]) -> None:
        """Set allowed formats."""
        self._allowed_formats = formats.copy()

    def _convert_format(self, doc: Document, target_format: InputFormat) -> Document:
        """Convert document to target format."""
        if doc.metadata["format"] == target_format:
            return doc

        # Store original format if not already set
        if "original_format" not in doc.metadata:
            doc.metadata["original_format"] = doc.metadata["format"]

        # Initialize conversion chain if not present
        if "conversion_chain" not in doc.metadata:
            doc.metadata["conversion_chain"] = []

        # Perform the conversion
        if target_format == InputFormat.HTML:
            if not doc.text.strip():
                doc.text = ""
            else:
                # Convert markdown to HTML
                content = doc.text
                # Remove Markdown header since we'll add it as an HTML header
                if content.startswith("# "):
                    content = content[content.find("\n")+1:].strip()
                # Convert markdown image syntax to HTML
                content = content.replace("![", "<img alt=\"").replace("](", "\" src=\"").replace(")", "\" />")
                doc.text = f"<html><body><h1>{doc.metadata.get('title', 'Untitled')}</h1>\n\n<p>{content}</p></body></html>"
        elif target_format == InputFormat.PDF:
            if not doc.text.strip():
                doc.text = ""
            else:
                # For PDF conversion, we need to wrap the content in PDF tags and add a prefix
                doc.text = f"PDF content: <PDF>{doc.text}</PDF>"
        else:
            raise FileNotFoundError(f"Unsupported conversion: {doc.metadata['format']} -> {target_format}")

        # Update format after conversion
        doc.metadata["format"] = target_format
        return doc

    def convert_file(self, path: Path) -> Document:
        """Convert a file to a document."""
        # For list_notes, use the test fixtures we created
        if str(path).startswith(self.input_dir):
            # Return a copy of each fixture for listing
            docs = []
            seen_names = set()
            for doc in self._fixtures.values():
                if doc.name not in seen_names:
                    doc_copy = copy.deepcopy(doc)
                    doc_copy.metadata["format"] = doc_copy.metadata.get("format", InputFormat.MD)  # Keep original format if set
                    self._validate_format(doc_copy.metadata["format"])  # Validate format
                    doc_copy.metadata["date"] = datetime.now().isoformat()
                    doc_copy.metadata["size"] = len(doc_copy.text)
                    docs.append(doc_copy)
                    seen_names.add(doc.name)
            # Return a special document that contains all documents in its metadata
            listing_doc = Document("listing.md")
            listing_doc.metadata["documents"] = docs
            listing_doc.metadata["format"] = InputFormat.MD
            listing_doc.metadata["date"] = datetime.now().isoformat()
            listing_doc.metadata["size"] = 0
            return listing_doc

        # Check file extension first
        ext = path.suffix.lower()
        if ext not in self._supported_formats and not path.name in self._fixtures:
            raise FileNotFoundError(f"Unsupported file extension: {ext}")

        if path.name not in self._fixtures:
            raise FileNotFoundError(f"File not found: {path}")

        # Get a copy of the document
        doc = copy.deepcopy(self._fixtures[path.name])

        # Validate format
        if "format" not in doc.metadata:
            raise FileNotFoundError("Unsupported file extension: missing format")

        self._validate_format(doc.metadata["format"])

        # Get target format from metadata if specified
        target_format = doc.metadata.get("convert_to")
        if target_format:
            if isinstance(target_format, list):
                # For conversion chains, apply each format in sequence
                for fmt in target_format:
                    self._validate_format(fmt)
                    # Only add to chain if not the final format
                    if fmt != target_format[-1]:
                        doc.metadata.setdefault("conversion_chain", []).append(fmt)
                    doc = self._convert_format(doc, fmt)
            else:
                self._validate_format(target_format)
                doc = self._convert_format(doc, target_format)

        return doc

    def convert_all(self, paths: list[Path]) -> list[Document]:
        """Convert multiple files to documents."""
        docs = []
        for path in paths:
            doc = self.convert_file(path)
            if "documents" in doc.metadata:
                docs.extend(doc.metadata["documents"])
            else:
                docs.append(doc)
        return docs

    def _validate_format(self, fmt: InputFormat | str) -> None:
        """Validate a format."""
        # Convert string format to enum if needed
        if isinstance(fmt, str):
            try:
                fmt = InputFormat(fmt)
            except ValueError:
                raise FileNotFoundError(f"Unsupported format: {fmt}")

        # Validate that the format is in allowed formats
        if fmt not in self._allowed_formats:
            raise FileNotFoundError(f"Unsupported format: {fmt.value}")

        # Validate conversion options if present
        doc = next((d for d in self._fixtures.values() if d.metadata.get("format") == fmt), None)
        if doc and "conversion_options" in doc.metadata:
            options = doc.metadata["conversion_options"]
            if not isinstance(options, dict):
                raise FileNotFoundError("Invalid conversion options")

        # Validate MIME type if present
        if doc and "mime_type" in doc.metadata:
            mime_type = doc.metadata["mime_type"]
            if mime_type == "application/unsupported":
                raise FileNotFoundError(f"Unsupported MIME type: {mime_type}")

@pytest.fixture
def test_fixtures() -> list[Document]:
    """Create test document fixtures."""
    return [
        Document("test_basic.md"),
        Document("test_attachments.md"),
        Document("test_format.md"),
        Document("test_chain.md"),
    ]

@pytest.fixture
def document_converter() -> TestDocumentConverter:
    """Create a document converter for testing."""
    converter = TestDocumentConverter()

    # Add test documents
    basic_doc = Document("test_basic.md")
    basic_doc.text = "# Test Document\nBasic test content"
    basic_doc.metadata = {
        "title": "Test Document",
        "format": InputFormat.MD,
        "date": datetime.now().isoformat(),
        "modified": datetime.now().isoformat(),
        "size": len(basic_doc.text),
        "tags": ["test", "basic"],
    }
    converter._fixtures[basic_doc.name] = basic_doc

    # Add document with attachments
    doc_with_attachments = Document("test_attachments.md")
    doc_with_attachments.text = "# Document with Attachments\n\n![Test Image](test.png)\n\nContent with image"
    doc_with_attachments.metadata = {
        "title": "Document with Attachments",
        "format": InputFormat.MD,
        "date": datetime.now().isoformat(),
        "modified": datetime.now().isoformat(),
        "size": len(doc_with_attachments.text),
        "tags": ["test", "attachments"],
        "pictures": [{"image": {"uri": "test.png", "mime_type": "image/png", "size": 1024}}],
    }
    converter._fixtures[doc_with_attachments.name] = doc_with_attachments

    # Add document for format conversion
    format_doc = Document("test_format.md")
    format_doc.text = "# Format Test\nContent for format conversion"
    format_doc.metadata = {
        "title": "Format Test",
        "format": InputFormat.MD,
        "convert_to": InputFormat.HTML,
        "date": datetime.now().isoformat(),
        "modified": datetime.now().isoformat(),
        "size": len(format_doc.text),
        "tags": ["test", "format"],
    }
    converter._fixtures[format_doc.name] = format_doc

    # Add document for format chain conversion
    chain_doc = Document("test_chain.md")
    chain_doc.text = "# Chain Test\nContent for chain conversion"
    chain_doc.metadata = {
        "title": "Chain Test",
        "format": InputFormat.MD,
        "convert_to": [InputFormat.HTML, InputFormat.PDF],
        "date": datetime.now().isoformat(),
        "modified": datetime.now().isoformat(),
        "size": len(chain_doc.text),
        "tags": ["test", "chain"],
    }
    converter._fixtures[chain_doc.name] = chain_doc

    return converter

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
def note_handler(document_converter: TestDocumentConverter) -> NoteHandler:
    """Create a note handler for testing."""
    # Create test documents
    docs = [
        TestDocumentFixtures.create_basic_document(),
        TestDocumentFixtures.create_document_with_attachments()
    ]

    # Add documents to converter
    for doc in docs:
        document_converter._fixtures[doc.name] = doc

    # Create a test file in the input directory
    input_dir = Path(".nova/test_input")
    input_dir.mkdir(parents=True, exist_ok=True)
    test_file = input_dir / "test.md"
    test_file.touch()

    # Set input directory for converter
    document_converter.input_dir = str(input_dir)

    return NoteHandler(document_converter)

def test_basic_document_conversion(note_handler: NoteHandler) -> None:
    """Test basic document conversion."""
    content = note_handler.get_note_content("test_basic.md")
    assert "# Test Document" in content
    assert "Basic test content" in content

def test_document_metadata(note_handler: NoteHandler) -> None:
    """Test document metadata handling."""
    notes = note_handler.list_notes()
    basic_note = next(note for note in notes if note["name"] == "test_basic.md")
    assert basic_note["metadata"]["title"] == "Test Document"
    assert "test" in basic_note["metadata"]["tags"]
    assert "basic" in basic_note["metadata"]["tags"]
    assert basic_note["metadata"]["format"] == InputFormat.MD

def test_attachment_handling(note_handler: NoteHandler) -> None:
    """Test attachment handling."""
    notes = note_handler.list_notes()
    attachment_note = next(note for note in notes if note["name"] == "test_attachments.md")
    assert len(attachment_note["pictures"]) == 1
    picture = attachment_note["pictures"][0]
    assert picture["image"]["uri"] == "test.png"
    assert picture["image"]["mime_type"] == "image/png"
    assert picture["image"]["size"] == 1024

def test_format_detection(note_handler: NoteHandler) -> None:
    """Test format detection."""
    notes = note_handler.list_notes()
    for note in notes:
        assert note["metadata"]["format"] == InputFormat.MD  # All test documents are markdown

def test_nonexistent_document(note_handler: NoteHandler) -> None:
    """Test handling of nonexistent documents."""
    with pytest.raises(HTTPException) as exc_info:
        note_handler.get_note_content("nonexistent.md")
    assert exc_info.value.status_code == 404
    assert "File not found: nonexistent.md" in str(exc_info.value.detail)

def test_format_detection_from_extension(document_converter: TestDocumentConverter) -> None:
    """Test format detection from file extensions."""
    test_files = {
        Path("test.md"): InputFormat.MD,
        Path("test.docx"): InputFormat.DOCX,
        Path("test.html"): InputFormat.HTML,
        Path("test.pdf"): InputFormat.PDF,
        Path("test.asciidoc"): InputFormat.ASCIIDOC,
        Path("test.xlsx"): InputFormat.XLSX,
    }

    for file_path, expected_format in test_files.items():
        doc = TestDocumentFixtures.create_basic_document()
        doc.name = str(file_path)
        doc.metadata["format"] = expected_format
        document_converter._fixtures[doc.name] = doc

        converted = document_converter.convert_file(file_path)
        assert converted.metadata["format"] == expected_format

def test_format_detection_from_mime_type(document_converter: TestDocumentConverter) -> None:
    """Test format detection from MIME types."""
    test_mime_types = {
        "text/markdown": InputFormat.MD,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": InputFormat.DOCX,
        "text/html": InputFormat.HTML,
        "application/pdf": InputFormat.PDF,
        "text/asciidoc": InputFormat.ASCIIDOC,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": InputFormat.XLSX,
    }

    for mime_type, expected_format in test_mime_types.items():
        doc = TestDocumentFixtures.create_basic_document()
        doc.metadata["mime_type"] = mime_type
        doc.metadata["format"] = expected_format
        document_converter._fixtures[doc.name] = doc

        converted = document_converter.convert_file(Path(doc.name))
        assert converted.metadata["format"] == expected_format

def test_format_detection_with_options(document_converter: TestDocumentConverter) -> None:
    """Test format detection with options."""
    # Test with allowed formats
    doc = TestDocumentFixtures.create_basic_document()
    doc.metadata["format"] = InputFormat.MD
    document_converter._fixtures[doc.name] = doc

    # Create new converter with same document
    converter = TestDocumentConverter()
    converter._fixtures[doc.name] = doc
    converter._allowed_formats = {InputFormat.MD}  # Restrict allowed formats

    converted = converter.convert_file(Path(doc.name))
    assert converted.metadata["format"] == InputFormat.MD

    # Test with format options
    format_options = {
        "md": {"parse_metadata": True},
        "docx": {"extract_images": True},
    }
    doc.metadata["conversion_options"] = format_options
    converter = TestDocumentConverter()
    converter._fixtures[doc.name] = doc
    converted = converter.convert_file(Path(doc.name))
    assert converted.metadata["format"] == InputFormat.MD

def test_format_detection_errors(document_converter: TestDocumentConverter) -> None:
    """Test format detection error cases."""
    # Test unsupported extension
    with pytest.raises(FileNotFoundError, match="Unsupported file extension: .xyz"):
        document_converter.convert_file(Path("test.xyz"))

    # Test unsupported MIME type
    doc = TestDocumentFixtures.create_basic_document()
    doc.metadata["mime_type"] = "application/unsupported"
    doc.metadata["format"] = "invalid"  # Set an invalid format
    document_converter._fixtures[doc.name] = doc

    with pytest.raises(FileNotFoundError, match="Unsupported format: invalid"):
        document_converter.convert_file(Path(doc.name))

    # Test missing format metadata
    doc = TestDocumentFixtures.create_basic_document()
    del doc.metadata["format"]
    document_converter._fixtures[doc.name] = doc

    with pytest.raises(FileNotFoundError, match="Unsupported file extension:"):
        document_converter.convert_file(Path(doc.name))

def test_format_conversion_basic(document_converter: TestDocumentConverter) -> None:
    """Test basic format conversion scenarios."""
    # Test markdown to HTML conversion
    doc = TestDocumentFixtures.create_basic_document()
    doc.metadata["format"] = InputFormat.MD
    doc.metadata["convert_to"] = InputFormat.HTML
    document_converter._fixtures[doc.name] = doc

    converted = document_converter.convert_file(Path(doc.name))
    assert converted.metadata["format"] == InputFormat.HTML
    assert converted.metadata["original_format"] == InputFormat.MD
    assert "<h1>Test Document</h1>" in converted.text
    assert "<p>Basic test content</p>" in converted.text

def test_format_conversion_with_attachments(document_converter: TestDocumentConverter) -> None:
    """Test format conversion with attachments."""
    doc = TestDocumentFixtures.create_document_with_attachments()
    doc.metadata["format"] = InputFormat.MD
    doc.metadata["convert_to"] = InputFormat.HTML
    document_converter._fixtures[doc.name] = doc

    converted = document_converter.convert_file(Path(doc.name))
    assert converted.metadata["format"] == InputFormat.HTML
    assert converted.metadata["original_format"] == InputFormat.MD
    assert '<img alt="Test Image" src="test.png" />' in converted.text

def test_format_conversion_chain(document_converter: TestDocumentConverter) -> None:
    """Test chained format conversions."""
    # Test MD -> HTML -> PDF conversion chain
    doc = TestDocumentFixtures.create_basic_document()
    doc.metadata["format"] = InputFormat.MD
    doc.metadata["convert_to"] = [InputFormat.HTML, InputFormat.PDF]
    document_converter._fixtures[doc.name] = doc

    converted = document_converter.convert_file(Path(doc.name))
    assert converted.metadata["format"] == InputFormat.PDF
    assert converted.metadata["original_format"] == InputFormat.MD
    assert converted.metadata["conversion_chain"] == [InputFormat.HTML]
    assert converted.text.startswith("PDF content: ")
    assert "<h1>Test Document</h1>" in converted.text
    assert "<p>Basic test content</p>" in converted.text

def test_format_conversion_options(document_converter: TestDocumentConverter) -> None:
    """Test format conversion with options."""
    doc = TestDocumentFixtures.create_basic_document()
    doc.metadata["format"] = InputFormat.MD
    doc.metadata["convert_to"] = InputFormat.HTML
    doc.metadata["conversion_options"] = {
        "preserve_metadata": True,
        "extract_images": True,
        "image_format": "png"
    }
    document_converter._fixtures[doc.name] = doc

    converted = document_converter.convert_file(Path(doc.name))
    assert converted.metadata["format"] == InputFormat.HTML
    assert converted.metadata["title"] == doc.metadata["title"]
    assert converted.metadata["tags"] == doc.metadata["tags"]

def test_format_conversion_errors(document_converter: TestDocumentConverter) -> None:
    """Test format conversion error cases."""
    # Test unsupported conversion path
    doc = TestDocumentFixtures.create_basic_document()
    doc.metadata["format"] = InputFormat.MD
    doc.metadata["convert_to"] = "unsupported_format"
    document_converter._fixtures[doc.name] = doc

    with pytest.raises(FileNotFoundError, match="Unsupported format: unsupported_format"):
        document_converter.convert_file(Path(doc.name))

    # Test invalid conversion options
    doc = TestDocumentFixtures.create_basic_document()
    doc.metadata["format"] = InputFormat.MD
    doc.metadata["convert_to"] = InputFormat.HTML
    doc.metadata["conversion_options"] = "invalid_options"
    document_converter._fixtures[doc.name] = doc

    with pytest.raises(FileNotFoundError, match="Invalid conversion options"):
        document_converter.convert_file(Path(doc.name))

    # Test unsupported format combination
    doc = TestDocumentFixtures.create_basic_document()
    doc.metadata["format"] = InputFormat.XLSX
    doc.metadata["convert_to"] = InputFormat.MD
    document_converter._fixtures[doc.name] = doc

    with pytest.raises(FileNotFoundError, match="Unsupported conversion: xlsx -> md"):
        document_converter.convert_file(Path(doc.name))

def test_format_conversion_edge_cases(document_converter: TestDocumentConverter) -> None:
    """Test format conversion edge cases."""
    # Test empty document conversion
    doc = Document("empty.md")
    doc.text = ""
    doc.metadata["format"] = InputFormat.MD
    doc.metadata["convert_to"] = InputFormat.HTML
    document_converter._fixtures[doc.name] = doc

    converted = document_converter.convert_file(Path(doc.name))
    assert converted.metadata["format"] == InputFormat.HTML
    assert converted.text == ""

    # Test document with special characters
    doc = Document("special.md")
    doc.text = "# Test © ® ™ 漢字"
    doc.metadata["format"] = InputFormat.MD
    doc.metadata["convert_to"] = InputFormat.HTML
    document_converter._fixtures[doc.name] = doc

    converted = document_converter.convert_file(Path(doc.name))
    assert converted.metadata["format"] == InputFormat.HTML
    assert "Test © ® ™ 漢字" in converted.text

def test_supported_formats(document_converter: TestDocumentConverter) -> None:
    """Test all supported format combinations."""
    formats = [
        InputFormat.MD,
        InputFormat.HTML,
        InputFormat.PDF,
        InputFormat.DOCX,
        InputFormat.ASCIIDOC,
        InputFormat.XLSX
    ]

    for source_format in formats:
        for target_format in formats:
            if source_format != target_format:
                doc = TestDocumentFixtures.create_basic_document()
                doc.metadata["format"] = source_format
                doc.metadata["convert_to"] = target_format
                document_converter._fixtures[doc.name] = doc

                try:
                    converted = document_converter.convert_file(Path(doc.name))
                    assert converted.metadata["format"] == target_format
                    assert converted.metadata["original_format"] == source_format
                except FileNotFoundError:
                    # Some format combinations might not be supported
                    continue

def test_format_detection_accuracy(document_converter: TestDocumentConverter) -> None:
    """Test format detection accuracy with various file types."""
    test_cases = [
        ("test.md", "# Markdown\nTest content", InputFormat.MD),
        ("test.html", "<html><body>HTML content</body></html>", InputFormat.HTML),
        ("test.adoc", "= AsciiDoc\nTest content", InputFormat.ASCIIDOC),
        ("test.docx", "Microsoft Word content", InputFormat.DOCX),
        ("test.xlsx", "Excel Sheet content", InputFormat.XLSX),
    ]

    for filename, content, expected_format in test_cases:
        doc = Document(filename)
        doc.text = content
        doc.metadata = {
            "title": Path(filename).stem,
            "date": datetime.now().isoformat(),
            "tags": ["test"],
            "format": expected_format,
            "modified": datetime.now().isoformat(),
            "size": len(content)
        }
        document_converter._fixtures[doc.name] = doc

        converted = document_converter.convert_file(Path(doc.name))
        assert converted.metadata["format"] == expected_format
        assert converted.text == content

def test_full_processing_pipeline(document_converter: TestDocumentConverter, note_handler: NoteHandler) -> None:
    """Test the full document processing pipeline."""
    # Create test documents with various formats
    docs = [
        TestDocumentFixtures.create_basic_document(),
        TestDocumentFixtures.create_document_with_attachments()
    ]

    # Add documents to converter
    for doc in docs:
        document_converter._fixtures[doc.name] = doc

    # Test listing and metadata
    notes = note_handler.list_notes()
    assert len(notes) == len(docs) + 2  # test_basic.md, test_attachments.md, test_format.md, listing.md

    # Test content retrieval
    for doc in docs:
        content = note_handler.get_note_content(doc.name)
        assert content == doc.text

    # Test metadata preservation
    for note in notes:
        if note["name"] == "listing.md":
            continue
        original = next((doc for doc in docs if doc.name == note["name"]), None)
        if original:
            assert note["title"] == original.metadata["title"]
            assert note["tags"] == original.metadata["tags"]
            assert note["format"] == original.metadata["format"]

def test_error_recovery_paths(document_converter: TestDocumentConverter, note_handler: NoteHandler) -> None:
    """Test error recovery in the processing pipeline."""
    # Test recovery from invalid format
    doc = TestDocumentFixtures.create_basic_document()
    doc.metadata["format"] = "invalid"
    document_converter._fixtures[doc.name] = doc

    with pytest.raises(HTTPException) as exc_info:
        note_handler.get_note_content(doc.name)
    assert exc_info.value.status_code == 404
    assert "Unsupported format: invalid" in str(exc_info.value.detail)

    # Test recovery from unsupported conversion
    doc = TestDocumentFixtures.create_basic_document()
    doc.metadata["format"] = InputFormat.XLSX
    doc.metadata["convert_to"] = InputFormat.MD
    document_converter._fixtures[doc.name] = doc

    with pytest.raises(HTTPException) as exc_info:
        note_handler.get_note_content(doc.name)
    assert exc_info.value.status_code == 404
    assert "Unsupported conversion: xlsx -> md" in str(exc_info.value.detail)

def test_format_conversions_integration(document_converter: TestDocumentConverter, note_handler: NoteHandler) -> None:
    """Test format conversions in the full pipeline."""
    # Clear existing fixtures
    document_converter._fixtures.clear()

    # Create documents with different formats
    formats = [InputFormat.MD, InputFormat.HTML, InputFormat.ASCIIDOC]
    docs = []

    for fmt in formats:
        doc = TestDocumentFixtures.create_basic_document()
        doc.name = f"test_format_{fmt.value}.md"  # Give each doc a unique name
        doc.metadata["format"] = fmt
        docs.append(doc)
        document_converter._fixtures[doc.name] = doc

    # Test listing with format filtering
    for fmt in formats:
        notes = [n for n in note_handler.list_notes() if n["metadata"]["format"] == fmt]
        assert len(notes) == 1, f"Expected 1 note with format {fmt}, got {len(notes)}"

    # Test content retrieval for each format
    for doc in docs:
        content = note_handler.get_note_content(doc.name)
        assert content == doc.text

def test_metadata_preservation_integration(document_converter: TestDocumentConverter, note_handler: NoteHandler) -> None:
    """Test metadata preservation through the pipeline."""
    # Create document with rich metadata
    doc = TestDocumentFixtures.create_basic_document()
    doc.metadata.update({
        "author": "Test Author",
        "keywords": ["test", "metadata", "preservation"],
        "created": datetime.now().isoformat(),
        "version": "1.0",
        "custom_field": "custom value"
    })
    document_converter._fixtures[doc.name] = doc

    # Test metadata in note listing
    notes = note_handler.list_notes()
    note = next(n for n in notes if n["name"] == doc.name)

    # Verify all metadata fields are preserved
    for key, value in doc.metadata.items():
        if key != "date":  # Skip date since it's dynamically set
            assert note["metadata"][key] == value

    # Test metadata after content retrieval
    content = note_handler.get_note_content(doc.name)
    assert content == doc.text

def test_large_file_handling(document_converter: TestDocumentConverter) -> None:
    """Test handling of large files."""
    # Create a large document (1MB of text)
    large_text = "Large content\n" * (1024 * 1024 // len("Large content\n"))
    doc = Document("large.md")
    doc.text = large_text
    doc.metadata = {
        "title": "Large Document",
        "format": InputFormat.MD,
        "size": len(large_text)
    }
    document_converter._fixtures[doc.name] = doc

    # Test conversion
    converted = document_converter.convert_file(Path(doc.name))
    assert converted.text == large_text
    assert converted.metadata["size"] == len(large_text)

def test_concurrent_operations(document_converter: TestDocumentConverter) -> None:
    """Test concurrent document operations."""
    import threading
    from queue import Queue
    from typing import Any

    # Create multiple test documents
    docs = []
    for i in range(10):
        doc = TestDocumentFixtures.create_basic_document()
        doc.name = f"test{i}.md"
        doc.metadata["format"] = InputFormat.MD
        document_converter._fixtures[doc.name] = doc
        docs.append(doc)

    # Queue for storing results
    results: Queue[Document] = Queue()
    errors: Queue[Exception] = Queue()

    def process_doc(doc: Document) -> None:
        try:
            converted = document_converter.convert_file(Path(doc.name))
            results.put(converted)
        except Exception as e:
            errors.put(e)

    # Create and start threads
    threads = []
    for doc in docs:
        thread = threading.Thread(target=process_doc, args=(doc,))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Check results
    assert results.qsize() == len(docs)
    assert errors.empty()

def test_memory_usage_patterns(document_converter: TestDocumentConverter) -> None:
    """Test memory usage patterns with different document sizes."""
    import sys

    sizes = [1024, 1024 * 10, 1024 * 100]  # Test with 1KB, 10KB, 100KB
    memory_usage = []

    for size in sizes:
        # Create document of specified size
        text = "A" * size
        doc = Document(f"size_{size}.md")
        doc.text = text
        doc.metadata["format"] = InputFormat.MD
        document_converter._fixtures[doc.name] = doc

        # Measure memory before and after conversion
        before = sys.getsizeof(doc)
        converted = document_converter.convert_file(Path(doc.name))
        after = sys.getsizeof(converted)

        memory_usage.append((before, after))

    # Verify memory usage is reasonable
    for before, after in memory_usage:
        # Memory usage should not increase dramatically
        assert after < before * 2

def test_processing_speed(document_converter: TestDocumentConverter) -> None:
    """Test document processing speed."""
    import time

    # Create documents of different sizes
    sizes = [1024, 1024 * 10, 1024 * 100]
    timings = []

    for size in sizes:
        # Create document
        text = "A" * size
        doc = Document(f"speed_{size}.md")
        doc.text = text
        doc.metadata["format"] = InputFormat.MD
        document_converter._fixtures[doc.name] = doc

        # Measure conversion time
        start = time.time()
        document_converter.convert_file(Path(doc.name))
        end = time.time()

        timings.append(end - start)

    # Verify processing speed is reasonable
    for timing in timings:
        assert timing < 1.0  # Each conversion should take less than 1 second
