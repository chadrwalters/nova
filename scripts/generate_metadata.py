#!/usr/bin/env python3
"""Script to generate metadata.json for Bear notes."""

import json
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)


def generate_metadata():
    """Generate metadata.json for Bear notes."""
    input_dir = Path(
        "/Users/chadwalters/Library/Mobile Documents/com~apple~CloudDocs/_NovaInput"
    )

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    metadata = {}
    for note_file in input_dir.glob("*.md"):
        try:
            # Get file stats
            stats = note_file.stat()
            creation_time = datetime.fromtimestamp(stats.st_ctime)
            modification_time = datetime.fromtimestamp(stats.st_mtime)

            # Get attachments
            attachments_dir = input_dir / note_file.stem
            attachments = []
            if attachments_dir.exists() and attachments_dir.is_dir():
                attachments = [
                    str(f.name) for f in attachments_dir.glob("*") if f.is_file()
                ]

            # Create metadata entry
            metadata[note_file.name] = {
                "title": note_file.stem,
                "creation_date": creation_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "modification_date": modification_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "tags": [],  # Tags will be extracted from content later
                "attachments": attachments,
            }
            logging.info(f"Generated metadata for {note_file.name}")

        except Exception as e:
            logging.error(f"Error processing {note_file.name}: {str(e)}")
            continue

    # Write metadata to file
    metadata_file = input_dir / "metadata.json"
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)

    logging.info(f"Metadata saved to {metadata_file}")
    logging.info(f"Generated metadata for {len(metadata)} notes")


if __name__ == "__main__":
    generate_metadata()
