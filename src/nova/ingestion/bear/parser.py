"""Parser for Bear.app note exports."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ...config import config
from .exceptions import (
    BearAttachmentError,
    BearParserError,
    InvalidBearExportError,
    InvalidBearNoteError,
)


@dataclass
class BearAttachment:
    """Represents an attachment in a Bear note."""

    filename: str
    path: Path
    content_type: str
    size: int
    created_at: datetime
    modified_at: datetime
    processed: bool = False
    processing_error: str | None = None


@dataclass
class BearNote:
    """Represents a Bear note with its content and metadata."""

    title: str
    content: str
    path: Path
    tags: set[str] = field(default_factory=set)
    attachments: list[BearAttachment] = field(default_factory=list)
    created_at: datetime | None = None
    modified_at: datetime | None = None
    metadata: dict[str, str] = field(default_factory=dict)


class BearParser:
    """Parser for Bear.app note exports."""

    def __init__(self, export_path: str | None = None) -> None:
        """Initialize the Bear parser.

        Args:
            export_path: Path to Bear export directory. If None, uses configured input_dir.
        """
        self.export_path = Path(export_path or config.get("paths.input_dir"))
        self.processing_path = Path(config.get("paths.processing_dir"))

        if not self.export_path.exists():
            raise InvalidBearExportError(
                f"Export directory not found: {self.export_path}"
            )

    def parse_note(self, note_path: Path) -> BearNote:
        """Parse a single Bear note file.

        Args:
            note_path: Path to the note file

        Returns:
            Parsed BearNote object

        Raises:
            InvalidBearNoteError: If the note file is malformed
        """
        if not note_path.exists():
            raise InvalidBearNoteError(f"Note file not found: {note_path}")

        try:
            with open(note_path, encoding="utf-8") as f:
                content = f.read()

            # Extract title from filename or first heading
            title = self._extract_title(note_path, content)

            # Extract tags from content
            tags = self._extract_tags(content)

            # Find attachments
            attachments = self._find_attachments(note_path)

            # Get file timestamps
            stats = note_path.stat()
            created_at = datetime.fromtimestamp(stats.st_ctime)
            modified_at = datetime.fromtimestamp(stats.st_mtime)

            return BearNote(
                title=title,
                content=content,
                path=note_path,
                tags=tags,
                attachments=attachments,
                created_at=created_at,
                modified_at=modified_at,
            )

        except Exception as e:
            raise InvalidBearNoteError(f"Failed to parse note {note_path}: {str(e)}")

    def parse_all(self) -> list[BearNote]:
        """Parse all notes in the export directory.

        Returns:
            List of parsed BearNote objects
        """
        notes = []
        for note_path in self.export_path.rglob("*.md"):
            try:
                note = self.parse_note(note_path)
                notes.append(note)
            except BearParserError as e:
                # Log error but continue processing other notes
                print(f"Error parsing {note_path}: {str(e)}")

        return notes

    def _extract_title(self, note_path: Path, content: str) -> str:
        """Extract note title from filename or content."""
        # Try filename first (removing .md extension)
        title = note_path.stem

        # Look for first heading in content
        lines = content.split("\n")
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
                break

        return title

    def _extract_tags(self, content: str) -> set[str]:
        """Extract Bear tags from note content."""
        tags = set()

        # Match #tag patterns (excluding code blocks)
        lines = content.split("\n")
        in_code_block = False

        for line in lines:
            # Toggle code block state
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue

            # Skip tag extraction in code blocks
            if in_code_block:
                continue

            # Find #tags but ignore URLs
            words = line.split()
            for word in words:
                if word.startswith("#") and not word.startswith("#/"):
                    # Remove trailing punctuation
                    tag = word.rstrip(".,!?:;")
                    # Remove leading #
                    tag = tag[1:]
                    if tag:
                        tags.add(tag)

        return tags

    def _find_attachments(self, note_path: Path) -> list[BearAttachment]:
        """Find attachments referenced in the note."""
        attachments = []

        # Look for attachment directory next to note
        attachments_dir = note_path.parent / "assets"
        if not attachments_dir.exists():
            return attachments

        # Process each file in attachments directory
        for attachment_path in attachments_dir.iterdir():
            try:
                stats = attachment_path.stat()

                attachment = BearAttachment(
                    filename=attachment_path.name,
                    path=attachment_path,
                    content_type=self._get_content_type(attachment_path),
                    size=stats.st_size,
                    created_at=datetime.fromtimestamp(stats.st_ctime),
                    modified_at=datetime.fromtimestamp(stats.st_mtime),
                )

                attachments.append(attachment)

            except Exception as e:
                raise BearAttachmentError(
                    f"Failed to process attachment {attachment_path}: {str(e)}"
                )

        return attachments

    def _get_content_type(self, path: Path) -> str:
        """Get content type based on file extension."""
        ext = path.suffix.lower()

        content_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }

        return content_types.get(ext, "application/octet-stream")
