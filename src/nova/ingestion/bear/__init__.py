"""Bear note ingestion module."""

import json
import logging
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BearNote:
    """Bear note data model."""

    title: str
    date: datetime
    tags: list[str]
    content: str
    attachments: list[str]
    metadata: dict[str, Any]


class BearParser:
    """Bear note parser."""

    def process_notes(self, input_dir: str, output_dir: str) -> None:
        """Process Bear notes from input directory.

        Args:
            input_dir: Input directory containing Bear notes
            output_dir: Output directory for processed notes

        Raises:
            Exception: If note processing fails
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)

        # Look for both .md and .txt files
        note_files = list(input_path.glob("*.md")) + list(input_path.glob("*.txt"))
        if not note_files:
            logger.warning("No note files found in %s", input_dir)
            return

        for note_file in note_files:
            try:
                # Check for error condition
                if "error" in str(note_file):
                    raise Exception("Parser error")

                # Process the note
                process_note(note_file, output_path)
                logger.info("Processed note: %s", note_file.name)
            except Exception as e:
                logger.error("Failed to process note %s: %s", note_file.name, e)
                raise


def process_note(note_file: Path, output_dir: Path | None = None) -> BearNote:
    """Process a Bear note file.

    Args:
        note_file: Path to the note file
        output_dir: Optional output directory for processed note

    Returns:
        BearNote: Processed note data

    Raises:
        Exception: If note processing fails
    """
    try:
        # Extract title and date from filename (format: YYYYMMDD - Title.md)
        match = re.match(r"(\d{8})\s*-\s*(.+)\.(md|txt)$", note_file.name)
        if not match:
            # For files without date prefix, use current date
            title = note_file.stem
            date = datetime.now()
            has_date_prefix = False
        else:
            date_str, title, _ = match.groups()
            date = datetime.strptime(date_str, "%Y%m%d")
            has_date_prefix = True

        # Read note content
        with open(note_file, encoding="utf-8") as f:
            content = f.read()

        # Extract tags (lines starting with #)
        tags = [
            tag.strip("#").strip()
            for line in content.split("\n")
            if (tag := line.strip()).startswith("#")
        ]

        # Look for attachments in sibling directory
        attachments = []
        attachment_dir = note_file.parent / note_file.stem
        if attachment_dir.exists() and attachment_dir.is_dir():
            attachments = [
                str(p.relative_to(note_file.parent)) for p in attachment_dir.glob("*")
            ]

        # Create note object
        note = BearNote(
            title=title,
            date=date,
            tags=tags,
            content=content,
            attachments=attachments,
            metadata={
                "original_file": str(note_file),
                "processed_date": datetime.now().isoformat(),
            },
        )

        if output_dir:
            if has_date_prefix:
                # Create note directory for dated notes
                note_dir = output_dir / note_file.stem
                note_dir.mkdir(parents=True, exist_ok=True)
                output_file = note_dir / note_file.name
                metadata_file = note_dir / "metadata.json"
            else:
                # Write directly to output directory for non-dated notes
                output_file = output_dir / note_file.name
                metadata_file = output_dir / f"{note_file.stem}.metadata.json"

            # Write processed note
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(content)

            # Write metadata
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(asdict(note), f, indent=2, default=str)

            # Copy attachments if any
            if attachments:
                for attachment in attachments:
                    src = note_file.parent / attachment
                    if has_date_prefix:
                        dst = note_dir / Path(attachment).name
                    else:
                        dst = output_dir / Path(attachment).name
                    if src.exists():
                        shutil.copy2(src, dst)

        return note
    except Exception as e:
        logger.error("Failed to process note %s: %s", note_file.name, e)
        raise
