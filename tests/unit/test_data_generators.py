"""Test data generators for docling integration."""

import random
from datetime import datetime, timedelta
from typing import Any

from nova.stubs.docling import Document, InputFormat


class TestDataGenerators:
    """Test data generators for docling integration."""

    _LOREM_IPSUM = """
    Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor
    incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis
    nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
    """.strip()

    _SAMPLE_TAGS = [
        "work",
        "personal",
        "todo",
        "ideas",
        "notes",
        "research",
        "meeting",
        "project",
        "draft",
        "final",
        "important",
        "urgent",
        "archive",
        "reference",
    ]

    _SAMPLE_AUTHORS = [
        "John Doe",
        "Jane Smith",
        "Alice Johnson",
        "Bob Wilson",
        "Carol Brown",
        "David Miller",
        "Eve Anderson",
        "Frank Thomas",
    ]

    _SAMPLE_CATEGORIES = [
        "Documentation",
        "Research",
        "Development",
        "Design",
        "Testing",
        "Planning",
        "Review",
        "Analysis",
    ]

    _SAMPLE_STATUSES = [
        "draft",
        "review",
        "approved",
        "published",
        "archived",
        "deprecated",
        "pending",
    ]

    @classmethod
    def generate_random_text(cls, paragraphs: int = 3) -> str:
        """Generate random text content.

        Args:
            paragraphs: Number of paragraphs to generate

        Returns:
            Generated text content
        """
        return "\n\n".join([cls._LOREM_IPSUM] * paragraphs)

    @classmethod
    def generate_random_tags(cls, min_tags: int = 1, max_tags: int = 5) -> list[str]:
        """Generate random tags.

        Args:
            min_tags: Minimum number of tags
            max_tags: Maximum number of tags

        Returns:
            List of random tags
        """
        num_tags = random.randint(min_tags, max_tags)
        return random.sample(cls._SAMPLE_TAGS, num_tags)

    @classmethod
    def generate_random_metadata(cls) -> dict[str, Any]:
        """Generate random metadata.

        Returns:
            Dictionary of random metadata
        """
        return {
            "author": random.choice(cls._SAMPLE_AUTHORS),
            "category": random.choice(cls._SAMPLE_CATEGORIES),
            "status": random.choice(cls._SAMPLE_STATUSES),
            "version": f"{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
            "priority": random.choice(["low", "medium", "high"]),
        }

    @classmethod
    def generate_random_date(cls, start_date: datetime | None = None) -> datetime:
        """Generate random date within the last year.

        Args:
            start_date: Optional start date (defaults to now)

        Returns:
            Random datetime
        """
        if start_date is None:
            start_date = datetime.now()
        days_ago = random.randint(0, 365)
        return start_date - timedelta(days=days_ago)

    @classmethod
    def generate_random_document(
        cls,
        input_format: InputFormat = InputFormat.MD,
        with_metadata: bool = True,
        with_images: bool = False,
    ) -> Document:
        """Generate a random document.

        Args:
            input_format: Document format
            with_metadata: Whether to include rich metadata
            with_images: Whether to include images

        Returns:
            Generated document
        """
        # Generate basic document
        doc = Document(f"test_{random.randint(1000, 9999)}.{input_format.value}")
        date = cls.generate_random_date()

        # Set content based on format
        if input_format == InputFormat.MD:
            doc.text = f"# {doc.name}\n\n{cls.generate_random_text()}"
        elif input_format == InputFormat.HTML:
            doc.text = f"<h1>{doc.name}</h1><p>{cls.generate_random_text()}</p>"
        elif input_format == InputFormat.ASCIIDOC:
            doc.text = f"= {doc.name}\n\n{cls.generate_random_text()}"
        else:
            doc.text = cls.generate_random_text()

        # Add basic metadata
        doc.metadata = {
            "title": doc.name,
            "date": date.isoformat(),
            "tags": cls.generate_random_tags(),
            "format": input_format.value,
            "modified": date.isoformat(),
            "size": len(doc.text),
        }

        # Add rich metadata if requested
        if with_metadata:
            doc.metadata.update(cls.generate_random_metadata())

        # Add images if requested
        if with_images:
            num_images = random.randint(1, 3)
            doc.pictures = []
            for i in range(num_images):
                width = random.randint(800, 1920)
                height = random.randint(600, 1080)
                doc.pictures.append(
                    {
                        "image": {
                            "uri": f"image_{i}.png",
                            "mime_type": "image/png",
                            "size": random.randint(1024, 10240),
                            "width": width,
                            "height": height,
                        }
                    }
                )

        return doc

    @classmethod
    def generate_document_batch(
        cls,
        num_documents: int,
        formats: list[InputFormat] | None = None,
        with_metadata: bool = True,
        with_images: bool = False,
    ) -> list[Document]:
        """Generate a batch of random documents.

        Args:
            num_documents: Number of documents to generate
            formats: List of formats to use (defaults to [MD])
            with_metadata: Whether to include rich metadata
            with_images: Whether to include images

        Returns:
            List of generated documents
        """
        if formats is None:
            formats = [InputFormat.MD]

        documents = []
        for _ in range(num_documents):
            doc_format = random.choice(formats)
            doc = cls.generate_random_document(
                input_format=doc_format,
                with_metadata=with_metadata,
                with_images=with_images,
            )
            documents.append(doc)

        return documents
