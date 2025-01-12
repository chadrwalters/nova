"""Bear parser module for processing Bear.app note exports."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .exceptions import BearParserError, AttachmentError, OCRError
from .ocr import EasyOcrModel


@dataclass
class BearAttachment:
    """Represents an attachment in a Bear note."""

    path: Path
    ocr_text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    ocr_model: EasyOcrModel | None = None

    def __post_init__(self) -> None:
        """Initialize the attachment."""
        self.ocr_model = EasyOcrModel()

    @property
    def is_image(self) -> bool:
        """Check if the attachment is an image."""
        return self.path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".bmp"}

    async def process_ocr(self, nova_dir: Path) -> None:
        """Process OCR for this attachment."""
        try:
            if not self.path.exists():
                raise AttachmentError(f"Attachment file not found: {self.path}")

            if not self.is_image:
                return

            if self.ocr_model is None:
                self.ocr_model = EasyOcrModel()

            self.metadata["ocr_status"] = "processing"
            text, confidence = await self.ocr_model(str(self.path))
            self.ocr_text = text
            self.metadata["ocr_confidence"] = confidence
            self.metadata["ocr_status"] = "success"
        except Exception as e:
            self.metadata["ocr_status"] = "failed"
            self.metadata["error"] = str(e)
            await self.save_placeholder(nova_dir)
            if isinstance(e, AttachmentError):
                raise
            raise OCRError(f"OCR processing failed for {self.path}: {str(e)}") from e

    async def save_placeholder(self, nova_dir: Path) -> None:
        """Save a placeholder file for failed OCR."""
        placeholder_dir = nova_dir / "placeholders" / "ocr"
        placeholder_dir.mkdir(parents=True, exist_ok=True)

        placeholder = {
            "type": "ocr_failure",
            "version": 1,
            "original_file": str(self.path),
            "ocr_status": self.metadata.get("ocr_status"),
            "error": self.metadata.get("error"),
            "timestamp": datetime.now().isoformat(),
        }

        placeholder_file = placeholder_dir / f"{self.path.stem}_ocr_failure.json"
        placeholder_file.write_text(json.dumps(placeholder))


@dataclass
class BearNote:
    """Represents a Bear note with its content and metadata."""

    title: str
    content: str
    metadata: dict[str, Any]
    attachments: list[BearAttachment] = field(default_factory=list)
    tags: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        """Initialize the note."""
        pass


class BearParser:
    """Parser for Bear note markdown files."""

    def __init__(self, notes_dir: Path, nova_dir: Path = Path(".nova")):
        self.notes_dir = notes_dir
        self.nova_dir = nova_dir
        self.metadata_file = notes_dir / "metadata.json"
        self._setup_nova_directory()

    def _setup_nova_directory(self) -> None:
        """Set up the .nova directory structure."""
        for subdir in ["placeholders/ocr", "processing/ocr", "logs"]:
            (self.nova_dir / subdir).mkdir(parents=True, exist_ok=True)

    def _load_metadata(self, note_file: Path) -> dict[str, Any]:
        """Load metadata for a specific note."""
        try:
            with open(self.metadata_file) as f:
                metadata = json.load(f)
                if note_file.name in metadata:
                    return dict[str, Any](metadata[note_file.name])
                return {}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    async def parse_note(self, note_file: Path) -> BearNote:
        """Parse a single note file and return a BearNote object."""
        try:
            note_metadata = self._load_metadata(note_file)
            content = note_file.read_text()
            note = BearNote(
                title=note_metadata.get("title", ""),
                content=content,
                metadata=note_metadata,
            )

            # Extract tags from content
            note.tags = self._extract_tags(content, note_metadata.get("tags", []))

            # Process attachments
            attachments = note_metadata.get("attachments", [])
            for attachment_info in attachments:
                if isinstance(attachment_info, str):
                    filename = attachment_info
                    metadata = {}
                else:
                    filename = attachment_info["filename"]
                    metadata = {
                        k: v for k, v in attachment_info.items() if k != "filename"
                    }

                attachment_path = note_file.parent / filename
                if not attachment_path.exists():
                    continue

                attachment = BearAttachment(path=attachment_path, metadata=metadata)
                note.attachments.append(attachment)

                if attachment.is_image:
                    await attachment.process_ocr(self.nova_dir)

            return note

        except Exception as e:
            raise BearParserError(f"Error parsing note {note_file}: {str(e)}") from e

    async def parse_directory(self) -> list[BearNote]:
        """Parse all notes in the directory."""
        notes = []
        errors = []

        for note_file in self.notes_dir.glob("*.md"):
            try:
                note = await self.parse_note(note_file)
                notes.append(note)
            except BearParserError as e:
                errors.append(str(e))
                logging.error(f"Failed to parse {note_file}: {str(e)}")

        if errors:
            logging.warning(f"Encountered {len(errors)} errors while processing notes")

        return notes

    async def cleanup_placeholders(self, max_age_days: int = 30) -> None:
        """Clean up old placeholder files."""
        placeholder_dir = self.nova_dir / "placeholders" / "ocr"
        if not placeholder_dir.exists():
            return

        cutoff_time = datetime.now() - timedelta(days=max_age_days)
        for placeholder_file in placeholder_dir.glob("*.json"):
            try:
                placeholder = json.loads(placeholder_file.read_text())
                timestamp = datetime.fromisoformat(placeholder["timestamp"])
                if timestamp < cutoff_time:
                    placeholder_file.unlink()
                    logging.info(f"Removed old placeholder: {placeholder_file}")
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logging.warning(
                    f"Error processing placeholder file {placeholder_file}: {str(e)}"
                )

    def _extract_tags(
        self, content: str, existing_tags: list[str] | None = None
    ) -> set[str]:
        """Extract tags from note content."""
        if existing_tags is None:
            existing_tags = []

        # Extract tags from content (e.g., #tag1 #tag2)
        # Ignore tags inside code blocks
        tags = set(existing_tags)
        in_code_block = False
        for line in content.split("\n"):
            if line.startswith("```"):
                in_code_block = not in_code_block
                continue

            if not in_code_block:
                for word in line.split():
                    if word.startswith("#") and len(word) > 1:
                        tags.add(word[1:])

        return tags
