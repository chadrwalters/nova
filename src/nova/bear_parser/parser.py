"""Nova Bear Parser Module.

This module provides functionality for parsing Bear note markdown files, handling
attachments and images, and extracting metadata like tags and creation dates.
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

import json
import time
import easyocr
import logging

from .exceptions import BearParserError, OCRError
from docling.models.base_ocr_model import BaseOcrModel

__all__ = ["BearParser", "BearNote", "BearAttachment"]


class EasyOcrModel(BaseOcrModel):
    def __init__(self, enabled: bool = True, options: dict[str, Any] = None):
        super().__init__(enabled, options or {})
        self.reader = easyocr.Reader(["en"])

    def __call__(self, image_path: str) -> tuple[str, float]:
        if not self.enabled:
            return "", 0.0

        try:
            result = self.reader.readtext(image_path)
            if not result:
                return "", 0.0

            text = " ".join(r[1] for r in result)
            confidence = sum(r[2] for r in result) / len(result)
            return text, confidence
        except Exception as e:
            logging.error(f"Error processing OCR for {image_path}: {str(e)}")
            return "", 0.0


@dataclass
class BearAttachment:
    """Represents an attachment in a Bear note."""

    path: Path
    metadata: dict[str, Any] = field(default_factory=dict)
    ocr_text: str = ""
    MIN_CONFIDENCE_THRESHOLD: float = 50.0

    def __post_init__(self):
        """Initialize OCR model after dataclass initialization."""
        self.ocr_model = EasyOcrModel(
            enabled=True, options={"bitmap_area_threshold": 0.1}
        )

    def generate_placeholder(self) -> dict[str, Any]:
        """Generate a placeholder for failed OCR processing."""
        return {
            "type": "ocr_failure",
            "version": 1,
            "original_file": str(self.path),
            "ocr_status": self.metadata.get("ocr_status", "failed"),
            "ocr_confidence": self.metadata.get("ocr_confidence", 0.0),
            "ocr_errors": self.metadata.get("ocr_errors", []),
            "error": self.metadata.get("ocr_error", ""),
            "timestamp": time.time(),
        }

    async def save_placeholder(self, nova_dir: Path) -> Path:
        """Save the placeholder file to the .nova directory."""
        # Create placeholders directory if it doesn't exist
        placeholders_dir = nova_dir / "placeholders" / "ocr"
        placeholders_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename based on original file
        placeholder_name = f"{self.path.stem}_ocr_placeholder_{int(time.time())}.json"
        placeholder_path = placeholders_dir / placeholder_name

        # Generate and save placeholder
        placeholder = self.generate_placeholder()

        with open(placeholder_path, "w", encoding="utf-8") as f:
            json.dump(placeholder, f, indent=2)

        return placeholder_path

    @property
    def is_image(self) -> bool:
        """Check if the attachment is an image."""
        return self.path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".bmp"}

    async def process_ocr(self) -> None:
        """Process OCR on the image attachment if it is an image."""
        if not self.is_image:
            return

        try:
            text, confidence = await self.ocr_model(str(self.path))
            self.ocr_text = text
            self.metadata["ocr_confidence"] = confidence
            self.metadata["ocr_status"] = (
                "success"
                if confidence >= self.MIN_CONFIDENCE_THRESHOLD
                else "low_confidence"
            )
        except Exception as e:
            self.metadata["ocr_confidence"] = 0
            self.metadata["ocr_status"] = "failed"
            self.metadata["ocr_error"] = str(e)
            raise OCRError(f"Failed to process OCR on {self.path}: {e}")


@dataclass
class BearNote:
    """Represents a Bear note with its content and metadata."""

    title: str
    content: str
    metadata: dict[str, Any]
    attachments: list[BearAttachment] = None
    tags: set = None

    def __post_init__(self):
        """Initialize collections after dataclass creation."""
        self.attachments = self.attachments or []
        self.tags = self.tags or set()


class BearParser:
    """Parser for Bear notes and their attachments."""

    def __init__(self, notes_dir: Path, nova_dir: Path | None = None):
        self.notes_dir = notes_dir
        self.nova_dir = nova_dir or Path.home() / ".nova"
        self._setup_nova_directory()

    def _setup_nova_directory(self) -> None:
        """Set up the .nova directory structure."""
        # Create main directories
        for subdir in ["placeholders/ocr", "processing", "logs"]:
            (self.nova_dir / subdir).mkdir(parents=True, exist_ok=True)

    def _load_metadata(self, note_filename: str) -> dict[str, Any]:
        """Load metadata for a specific note."""
        metadata_path = self.notes_dir / "metadata.json"
        if not metadata_path.exists():
            raise BearParserError(f"No metadata found at {metadata_path}")

        try:
            with open(metadata_path, encoding="utf-8") as f:
                all_metadata = json.load(f)
                note_key = Path(note_filename).name
                if note_key not in all_metadata:
                    raise BearParserError(f"No metadata found for note {note_filename}")
                return all_metadata[note_key]
        except json.JSONDecodeError as e:
            raise BearParserError(f"Invalid metadata JSON: {str(e)}") from e

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
                    await attachment.process_ocr()

            return note

        except Exception as e:
            raise BearParserError(f"Error parsing note {note_file}: {str(e)}") from e

    async def parse_directory(self) -> list[BearNote]:
        """Parse all Bear notes in the directory."""
        notes = []
        errors = []

        for note_file in self.notes_dir.glob("*.md"):
            try:
                note = await self.parse_note(note_file)
                notes.append(note)
            except Exception as e:
                errors.append(f"Error processing {note_file.name}: {str(e)}")
                logging.error(f"Failed to parse {note_file}: {str(e)}", exc_info=True)

        if errors:
            logging.warning(f"Encountered {len(errors)} errors while processing notes")

        return notes

    async def cleanup_placeholders(self, max_age_days: int = 30) -> None:
        """Clean up old placeholder files."""
        placeholders_dir = self.nova_dir / "placeholders" / "ocr"
        if not placeholders_dir.exists():
            return

        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60

        for placeholder_file in placeholders_dir.glob("*.json"):
            try:
                stats = placeholder_file.stat()
                age = current_time - stats.st_mtime
                if age > max_age_seconds:
                    placeholder_file.unlink()
                    logging.info(f"Removed old placeholder: {placeholder_file}")
            except Exception as e:
                logging.error(f"Error cleaning up {placeholder_file}: {str(e)}")

    def _extract_tags(self, content: str, existing_tags: list[str] = None) -> set:
        """Extract tags from note content."""
        tags = set(existing_tags or [])

        # Split content into lines and process each line
        lines = content.split("\n")
        in_code_block = False

        for line in lines:
            # Skip tags in code blocks
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                continue

            # Find all #tags in the line
            words = line.split()
            for word in words:
                # Basic tag format: #tag
                if word.startswith("#"):
                    tag = word[1:]
                    # Remove punctuation at the end of tags
                    tag = tag.rstrip(".,!?:;")
                    if tag:
                        tags.add(tag)

                # Nested tags: #tag/subtag
                elif "/#" in word:
                    parts = word.split("/#")
                    for part in parts:
                        tag = part.strip("#")
                        tag = tag.rstrip(".,!?:;")
                        if tag:
                            tags.add(tag)

        return tags
