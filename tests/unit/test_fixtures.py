"""Test fixtures for docling integration."""

from datetime import datetime

from nova.stubs.docling import Document, InputFormat


class DocumentFixtures:
    """Document fixtures for testing."""

    @staticmethod
    def create_markdown_document(name: str = "test.md") -> Document:
        """Create a markdown document."""
        doc = Document(name)
        doc.text = "# Test Document\n\nThis is a test document in markdown format."
        doc.metadata = {
            "title": "Test Document",
            "date": datetime.now().isoformat(),
            "tags": ["test", "markdown"],
            "format": InputFormat.MD.value,
            "modified": datetime.now().isoformat(),
            "size": 52,
        }
        return doc

    @staticmethod
    def create_html_document(name: str = "test.html") -> Document:
        """Create an HTML document."""
        doc = Document(name)
        doc.text = "<h1>Test Document</h1><p>This is a test document in HTML format.</p>"
        doc.metadata = {
            "title": "Test Document",
            "date": datetime.now().isoformat(),
            "tags": ["test", "html"],
            "format": InputFormat.HTML.value,
            "modified": datetime.now().isoformat(),
            "size": 65,
        }
        return doc

    @staticmethod
    def create_asciidoc_document(name: str = "test.adoc") -> Document:
        """Create an AsciiDoc document."""
        doc = Document(name)
        doc.text = "= Test Document\n\nThis is a test document in AsciiDoc format."
        doc.metadata = {
            "title": "Test Document",
            "date": datetime.now().isoformat(),
            "tags": ["test", "asciidoc"],
            "format": InputFormat.ASCIIDOC.value,
            "modified": datetime.now().isoformat(),
            "size": 55,
        }
        return doc

    @staticmethod
    def create_document_with_image(name: str = "test_image.md") -> Document:
        """Create a document with an image."""
        doc = Document(name)
        doc.text = "# Document with Image\n\n![Test Image](test.png)\n\nThis document has an image."
        doc.metadata = {
            "title": "Document with Image",
            "date": datetime.now().isoformat(),
            "tags": ["test", "image"],
            "format": InputFormat.MD.value,
            "modified": datetime.now().isoformat(),
            "size": 82,
        }
        doc.pictures = [
            {
                "image": {
                    "uri": "test.png",
                    "mime_type": "image/png",
                    "size": 1024,
                    "width": 800,
                    "height": 600,
                }
            }
        ]
        return doc

    @staticmethod
    def create_document_with_table(name: str = "test_table.md") -> Document:
        """Create a document with a table."""
        doc = Document(name)
        doc.text = """# Document with Table

| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
| Cell 3   | Cell 4   |

This document has a table."""
        doc.metadata = {
            "title": "Document with Table",
            "date": datetime.now().isoformat(),
            "tags": ["test", "table"],
            "format": InputFormat.MD.value,
            "modified": datetime.now().isoformat(),
            "size": 120,
        }
        return doc

    @staticmethod
    def create_document_with_code(name: str = "test_code.md") -> Document:
        """Create a document with code blocks."""
        doc = Document(name)
        doc.text = """# Document with Code

```python
def hello_world():
    print("Hello, World!")
```

This document has a code block."""
        doc.metadata = {
            "title": "Document with Code",
            "date": datetime.now().isoformat(),
            "tags": ["test", "code"],
            "format": InputFormat.MD.value,
            "modified": datetime.now().isoformat(),
            "size": 98,
        }
        return doc

    @staticmethod
    def create_document_with_metadata(name: str = "test_metadata.md") -> Document:
        """Create a document with rich metadata."""
        doc = Document(name)
        doc.text = "# Document with Metadata\n\nThis document has rich metadata."
        doc.metadata = {
            "title": "Document with Metadata",
            "date": datetime.now().isoformat(),
            "tags": ["test", "metadata", "important"],
            "format": InputFormat.MD.value,
            "modified": datetime.now().isoformat(),
            "size": 45,
            "author": "Test Author",
            "version": "1.0.0",
            "status": "draft",
            "category": "test",
            "priority": "high",
        }
        return doc


def get_all_test_documents() -> list[Document]:
    """Get all test documents."""
    return [
        DocumentFixtures.create_markdown_document(),
        DocumentFixtures.create_html_document(),
        DocumentFixtures.create_asciidoc_document(),
        DocumentFixtures.create_document_with_image(),
        DocumentFixtures.create_document_with_table(),
        DocumentFixtures.create_document_with_code(),
        DocumentFixtures.create_document_with_metadata(),
    ]
