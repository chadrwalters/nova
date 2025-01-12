"""Bear note parser implementation."""

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


class BearParserError(Exception):
    """Error raised when parsing Bear notes fails."""


@dataclass
class BearAttachment:
    """Bear note attachment."""

    path: Path
    metadata: dict = field(default_factory=dict)


@dataclass
class BearNote:
    """Bear note."""

    title: str
    content: str
    tags: list[str]
    attachments: list[BearAttachment]
    metadata: dict = field(default_factory=dict)


class BearParser:
    """Parser for Bear notes."""

    def __init__(self, input_dir: Path) -> None:
        """Initialize the parser.

        Args:
            input_dir: Input directory containing Bear notes
        """
        self.input_dir = input_dir

    def parse_directory(self) -> list[BearNote]:
        """Parse all notes in the input directory.

        Returns:
            List of parsed notes
        """
        notes = []
        for note_file in self.input_dir.glob("**/*.md"):
            try:
                note = self.parse_note(note_file)
                notes.append(note)
            except Exception as e:
                logger.error(f"Failed to parse note {note_file}: {str(e)}")
        return notes

    def parse_note(self, note_file: Path) -> BearNote:
        """Parse a single note file.

        Args:
            note_file: Path to the note file

        Returns:
            Parsed note

        Raises:
            BearParserError: If parsing fails
        """
        try:
            content = note_file.read_text()
            title = self._extract_title(content)
            tags = self._extract_tags(content)
            attachments = self._extract_attachments(content, note_file.parent)
            return BearNote(
                title=title, content=content, tags=tags, attachments=attachments
            )
        except Exception as e:
            raise BearParserError(f"Failed to parse note {note_file}: {str(e)}")

    def _extract_title(self, content: str) -> str:
        """Extract title from note content.

        Args:
            content: Note content

        Returns:
            Note title
        """
        lines = content.split("\n")
        for line in lines:
            if line.startswith("# "):
                return line[2:].strip()
        return "Untitled Note"

    def _extract_tags(self, content: str) -> list[str]:
        """Extract tags from note content.

        Args:
            content: Note content

        Returns:
            List of tags
        """
        tags = []
        for line in content.split("\n"):
            if "#" in line:
                # Extract tags (words starting with #)
                words = line.split()
                tags.extend(
                    [
                        word[1:]
                        for word in words
                        if word.startswith("#") and len(word) > 1
                    ]
                )
        return list(set(tags))

    def _extract_attachments(
        self, content: str, note_dir: Path
    ) -> list[BearAttachment]:
        """Extract attachments from note content.

        Args:
            content: Note content
            note_dir: Directory containing the note

        Returns:
            List of attachments
        """
        attachments = []
        for line in content.split("\n"):
            if "![" in line and "](" in line:
                # Extract image path from markdown link
                path_start = line.find("](") + 2
                path_end = line.find(")", path_start)
                if path_start > 1 and path_end > path_start:
                    path = line[path_start:path_end].strip()
                    attachment_path = note_dir / path
                    if attachment_path.exists():
                        attachments.append(BearAttachment(path=attachment_path))
        return attachments
