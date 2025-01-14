"""Bear note parser implementation."""

import json
import logging
import time
from datetime import datetime
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar
from collections.abc import Callable

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

T = TypeVar("T")


def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry decorator for handling transient errors."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_error = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if attempt == max_retries:
                        break
                    time.sleep(current_delay)
                    current_delay *= backoff

            # If we get here, all retries failed
            if last_error is not None:
                raise last_error
            raise Exception("Unknown error occurred")

        return wrapper

    return decorator


class InputFormat(str, Enum):
    """Input format for Bear notes."""

    TEXT = "text"
    MARKDOWN = "markdown"


# Format to file extension mappings
FORMAT_TO_EXTENSIONS = {
    InputFormat.TEXT: [".txt"],
    InputFormat.MARKDOWN: [".md", ".markdown"],
}

# Format to MIME type mappings
FORMAT_TO_MIME_TYPE = {
    InputFormat.TEXT: "text/plain",
    InputFormat.MARKDOWN: "text/markdown",
}


class BearParserError(Exception):
    """Base exception for Bear parser errors."""

    pass


class AttachmentError(BearParserError):
    """Exception raised when processing an attachment."""

    pass


class UnsupportedFormatError(BearParserError):
    """Exception raised when a file format is not supported."""

    pass


class DocItemLabel(str, Enum):
    """Document item labels."""

    TEXT = "text"
    KEY_VALUE_REGION = "key_value_region"


class GroupLabel(str, Enum):
    """Group labels for document sections."""

    METADATA = "key_value_area"
    CONTENT = "section"
    HEADER = "section"
    FOOTER = "section"


class DocItem(BaseModel):
    """Base class for document items."""

    self_ref: str = Field(description="Reference to the item")
    orig: str = Field(description="Original text")
    text: str = Field(description="Processed text")
    label: str = Field(description="Item label")


class TextItem(DocItem):
    """Text item in a document."""

    label: DocItemLabel = Field(
        default=DocItemLabel.TEXT, description="Text item label"
    )


class KeyValueItem(DocItem):
    """Key-value item in a document."""

    label: DocItemLabel = Field(
        default=DocItemLabel.KEY_VALUE_REGION, description="Key-value item label"
    )


class GroupItem(BaseModel):
    """Group of items in a document."""

    self_ref: str = Field(description="Reference to the group")
    label: GroupLabel = Field(description="Group label")
    items: list[DocItem] = Field(
        default_factory=list, description="List of items in the group"
    )


class BearDocument(BaseModel):
    """Bear note document that follows the Docling document schema."""

    schema_name: str = Field(
        default="DoclingDocument", description="Schema name for the document"
    )
    version: str = Field(default="1.0.0", description="Schema version")
    name: str = Field(description="Document title")
    origin: str | None = Field(
        default=None, description="Original source of the document"
    )
    furniture: GroupItem | None = Field(default=None, description="Document furniture")
    groups: list[GroupItem] = Field(default_factory=list, description="Document groups")
    texts: list[TextItem] = Field(
        default_factory=list, description="Text items in the document"
    )
    pictures: list[DocItem] = Field(
        default_factory=list, description="Picture items in the document"
    )
    tables: list[DocItem] = Field(
        default_factory=list, description="Table items in the document"
    )
    key_value_items: list[KeyValueItem] = Field(
        default_factory=list, description="Key-value items in the document"
    )
    pages: dict[str, Any] = Field(default_factory=dict, description="Document pages")
    attachments: list[str] = Field(
        default_factory=list, description="Document attachments"
    )

    def __init__(
        self,
        title: str,
        content: str,
        date: str | None = None,
        tags: list[str] | None = None,
        input_format: InputFormat = InputFormat.TEXT,
    ) -> None:
        """Initialize document.

        Args:
            title: Document title
            content: Document content
            date: Optional document date
            tags: Optional list of tags
            input_format: Input format (text or markdown)
        """
        super().__init__(
            schema_name="DoclingDocument",
            version="1.0.0",
            name=title,
        )

        # Add content as text item
        text_item = TextItem(
            self_ref="#/content",
            orig=content,
            text=content,
            label=DocItemLabel.TEXT,
        )
        self.texts.append(text_item)

        # Add metadata as key-value items
        metadata_group = GroupItem(
            self_ref="#/metadata",
            label=GroupLabel.METADATA,
            items=[
                KeyValueItem(
                    self_ref="#/metadata/title",
                    orig=title,
                    text=title,
                    label=DocItemLabel.KEY_VALUE_REGION,
                ),
                KeyValueItem(
                    self_ref="#/metadata/format",
                    orig=input_format.value,
                    text=input_format.value,
                    label=DocItemLabel.KEY_VALUE_REGION,
                ),
            ],
        )

        # Add date if present
        if date:
            metadata_group.items.append(
                KeyValueItem(
                    self_ref="#/metadata/date",
                    orig=date,
                    text=date,
                    label=DocItemLabel.KEY_VALUE_REGION,
                )
            )
        else:
            # Use current date if not provided
            current_date = datetime.now().isoformat()
            metadata_group.items.append(
                KeyValueItem(
                    self_ref="#/metadata/date",
                    orig=current_date,
                    text=current_date,
                    label=DocItemLabel.KEY_VALUE_REGION,
                )
            )

        # Add tags if present
        if tags:
            tags_text = ",".join(tags)
            metadata_group.items.append(
                KeyValueItem(
                    self_ref="#/metadata/tags",
                    orig=tags_text,
                    text=tags_text,
                    label=DocItemLabel.KEY_VALUE_REGION,
                )
            )

        self.groups.append(metadata_group)

    @property
    def title(self) -> str:
        """Get the document title."""
        return self.name

    @property
    def content(self) -> str:
        """Get the document content."""
        text_items = [
            item
            for item in self.texts
            if isinstance(item, TextItem) and item.label == DocItemLabel.TEXT
        ]
        return text_items[0].text if text_items else ""

    @property
    def tags(self) -> list[str]:
        """Get the document tags."""
        for group in self.groups:
            if group.label == GroupLabel.METADATA:
                for item in group.items:
                    if item.self_ref == "#/metadata/tags":
                        return (
                            [tag.strip() for tag in item.text.split(",")]
                            if item.text
                            else []
                        )
        return []

    @property
    def date(self) -> datetime:
        """Get the document date."""
        for group in self.groups:
            if group.label == GroupLabel.METADATA:
                for item in group.items:
                    if item.self_ref == "#/metadata/date":
                        return datetime.fromisoformat(item.text)
        return datetime.now()  # Default to current time if not found

    def model_dump_json(self, **kwargs: Any) -> str:
        """Serialize to JSON.

        Args:
            **kwargs: Additional arguments passed to json.dumps

        Returns:
            JSON string representation of the document
        """
        return json.dumps(self.model_dump(), **kwargs)


class BearNote:
    """Bear note representation."""

    def __init__(
        self,
        title: str,
        content: str,
        date: datetime | None = None,
        tags: list[str] | None = None,
        attachments: list[str] | None = None,
        input_format: InputFormat = InputFormat.TEXT,
    ) -> None:
        """Initialize note.

        Args:
            title: Note title
            content: Note content
            date: Optional note date
            tags: Optional list of tags
            attachments: Optional list of attachments
            input_format: Input format (text or markdown)
        """
        self.title = title
        self.content = content
        self.date = date or datetime.now()
        self.tags = tags or []
        self.attachments = attachments or []
        self.input_format = input_format

    def to_docling(self) -> BearDocument:
        """Convert to Docling document."""
        return BearDocument(
            title=self.title,
            content=self.content,
            date=self.date.isoformat(),
            tags=self.tags,
            input_format=self.input_format,
        )

    def __str__(self) -> str:
        """Get string representation.

        Returns:
            String representation
        """
        return f"BearNote(title={self.title}, date={self.date}, tags={self.tags})"

    def __repr__(self) -> str:
        """Get string representation.

        Returns:
            String representation
        """
        return self.__str__()


class BearParser:
    """Parser for Bear notes."""

    def __init__(self, input_dir: str | Path) -> None:
        """Initialize parser.

        Args:
            input_dir: Input directory path
        """
        self.input_dir = Path(input_dir)
        self._notes: list[BearNote] = []  # Initialize as empty list
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Ensure notes are parsed if needed."""
        if not self._initialized:
            self.parse_directory()

    def _extract_tags(self, content: str) -> list[str]:
        """Extract tags from content.

        Args:
            content: Note content

        Returns:
            List of tags
        """
        tags = []
        words = content.split()
        for word in words:
            if word.startswith("#") and len(word) > 1:
                tags.append(word[1:])  # Remove the # prefix
        return tags

    def _parse_title_and_date(self, filename: str) -> tuple[str, datetime | None]:
        """Parse title and date from filename.

        Args:
            filename: Note filename

        Returns:
            Tuple of (title, date)
        """
        # Remove extension
        name = Path(filename).stem

        # Check for date prefix (YYYYMMDD - Title)
        parts = name.split(" - ", 1)
        if len(parts) == 2 and len(parts[0]) == 8 and parts[0].isdigit():
            try:
                date = datetime.strptime(parts[0], "%Y%m%d")
                return parts[1], date
            except ValueError:
                pass

        return name, None

    def parse_directory(self) -> None:
        """Parse all notes in the input directory."""
        if self._initialized:
            return

        logger.info("Parsing directory: %s", self.input_dir)

        if not self.input_dir.exists():
            logger.warning("Input directory does not exist: %s", self.input_dir)
            self._initialized = True
            return

        if not self.input_dir.is_dir():
            logger.error("Input path is not a directory: %s", self.input_dir)
            raise BearParserError(f"Input path is not a directory: {self.input_dir}")

        # Look for both .txt and .md files
        note_files = list(self.input_dir.glob("*.txt"))
        note_files.extend(self.input_dir.glob("*.md"))

        if not note_files:
            logger.info("No notes found in directory: %s", self.input_dir)
            self._initialized = True
            return

        for note_file in note_files:
            try:
                logger.debug("Processing note: %s", note_file)
                content = note_file.read_text()
                title, date = self._parse_title_and_date(note_file.name)
                tags = self._extract_tags(content)

                # Use appropriate input format based on file extension
                input_format = (
                    InputFormat.MARKDOWN
                    if note_file.suffix.lower() == ".md"
                    else InputFormat.TEXT
                )

                note = BearNote(
                    title=title,
                    content=content,
                    date=date,
                    tags=tags,
                    input_format=input_format,
                )
                self._notes.append(note)
                logger.debug("Successfully processed note: %s", note)

            except Exception as e:
                logger.error("Failed to process note %s: %s", note_file, e)
                # Continue processing other notes instead of failing completely
                continue

        logger.info("Successfully parsed %d notes", len(self._notes))
        self._initialized = True

    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def process_notes(self, output_dir: Path | None = None) -> list[BearDocument]:
        """Process all notes in the input directory.

        Args:
            output_dir: Optional output directory for processed notes

        Returns:
            List of BearDocument instances

        Raises:
            BearParserError: If processing fails
        """
        # Parse notes if not already done
        self._ensure_initialized()

        # Convert notes to BearDocument instances
        documents = []
        for note in self._notes:
            try:
                logger.debug("Converting note to document: %s", note)
                # Convert note to docling document
                doc = note.to_docling()

                # Save document if output directory is provided
                if output_dir:
                    output_path = output_dir / f"{note.title}.json"
                    output_path.write_text(doc.model_dump_json())
                    logger.debug("Saved document to: %s", output_path)

                documents.append(doc)

            except Exception as e:
                logger.error("Failed to process note %s: %s", note.title, e)
                # Continue processing other notes instead of failing completely
                continue

        logger.info("Successfully processed %d notes", len(documents))
        return documents


def get_format_from_extension(extension: str) -> InputFormat:
    """Get input format from file extension.

    Args:
        extension: File extension (e.g. ".txt", ".md")

    Returns:
        Input format

    Raises:
        UnsupportedFormatError: If extension not supported
    """
    for fmt, exts in FORMAT_TO_EXTENSIONS.items():
        if extension in exts:
            return fmt
    raise UnsupportedFormatError(f"Unsupported file extension: {extension}")


def get_format_from_mime_type(mime_type: str) -> InputFormat:
    """Get input format from MIME type.

    Args:
        mime_type: MIME type (e.g. "text/plain", "text/markdown")

    Returns:
        Input format

    Raises:
        UnsupportedFormatError: If MIME type not supported
    """
    for fmt, mime in FORMAT_TO_MIME_TYPE.items():
        if mime_type == mime:
            return fmt
    raise UnsupportedFormatError(f"Unsupported MIME type: {mime_type}")
