#!/usr/bin/env python3
"""Script to process Bear notes using the BearParser."""
import asyncio
import logging
from pathlib import Path

from nova.bear_parser.parser import BearParser

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


async def process_notes():
    """Process notes in the input directory."""
    # Set up paths
    input_dir = Path(
        "/Users/chadwalters/Library/Mobile Documents/com~apple~CloudDocs/_NovaInput"
    )
    nova_dir = Path("src/.nova")

    # Ensure input directory exists
    if not input_dir.exists():
        logging.error(f"Input directory not found: {input_dir}")
        return

    # Create .nova directory if it doesn't exist
    nova_dir.mkdir(parents=True, exist_ok=True)

    logging.info(f"Processing notes from: {input_dir}")
    logging.info(f"Using .nova directory: {nova_dir}")

    # Initialize parser and process notes
    parser = BearParser(notes_dir=input_dir, nova_dir=nova_dir)
    try:
        notes = await parser.parse_directory()
        logging.info(f"Successfully processed {len(notes)} notes")

        # Log details about each note
        for note in notes:
            logging.info(f"Note: {note.title}")
            logging.info(f"  Tags: {note.tags}")
            logging.info(f"  Attachments: {len(note.attachments)}")

            # Log OCR results for image attachments
            for attachment in note.attachments:
                if attachment.is_image:
                    ocr_status = attachment.metadata.get("ocr_status", "unknown")
                    ocr_confidence = attachment.metadata.get("ocr_confidence", 0)
                    logging.info(f"  Image: {attachment.path.name}")
                    logging.info(f"    OCR Status: {ocr_status}")
                    logging.info(f"    OCR Confidence: {ocr_confidence}")

    except Exception as e:
        logging.error(f"Error processing notes: {str(e)}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(process_notes())
