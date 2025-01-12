#!/usr/bin/env python3
"""Script to generate metadata.json for Bear notes."""
import json
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def generate_metadata(notes_dir: Path) -> None:
    """Generate metadata.json for Bear notes."""
    try:
        metadata = {}

        # Process each markdown file
        for note_file in notes_dir.glob("*.md"):
            # Get file stats
            stats = note_file.stat()
            created = datetime.fromtimestamp(stats.st_ctime).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            modified = datetime.fromtimestamp(stats.st_mtime).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

            # Get title from filename
            title = note_file.stem

            # Check for attachments
            attachments_dir = notes_dir / note_file.stem
            attachments = []
            if attachments_dir.exists() and attachments_dir.is_dir():
                for attachment in attachments_dir.glob("*"):
                    if attachment.is_file():
                        attachments.append(str(attachment.name))

            # Create note metadata
            metadata[note_file.name] = {
                "title": title,
                "creation_date": created,
                "modification_date": modified,
                "tags": [],  # We'll extract these from content later
                "attachments": attachments,
            }

        # Write metadata file
        metadata_path = notes_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Generated metadata for {len(metadata)} notes at {metadata_path}")

    except Exception as e:
        logger.error(f"Error generating metadata: {str(e)}", exc_info=True)


def main() -> None:
    """Main entry point."""
    input_dir = Path(
        "/Users/chadwalters/Library/Mobile Documents/com~apple~CloudDocs/_NovaInput"
    )

    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        return

    logger.info(f"Generating metadata for notes in: {input_dir}")
    generate_metadata(input_dir)


if __name__ == "__main__":
    main()
