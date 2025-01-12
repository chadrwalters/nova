#!/usr/bin/env python3
"""CLI script to process Bear notes using the BearParser."""
import asyncio
import logging
from pathlib import Path

from nova.bear_parser.parser import BearParser

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def process_notes(input_dir: Path, nova_dir: Path) -> None:
    """Process all notes in the input directory."""
    try:
        parser = BearParser(notes_dir=input_dir, nova_dir=nova_dir)
        notes = await parser.parse_directory()
        logger.info(f"Successfully processed {len(notes)} notes")

        # Print summary of processed notes
        for note in notes:
            logger.info(f"\nNote: {note.title}")
            logger.info(f"Tags: {', '.join(note.tags) if note.tags else 'No tags'}")
            if note.attachments:
                logger.info(f"Attachments: {len(note.attachments)}")
                for attachment in note.attachments:
                    if attachment.is_image:
                        ocr_status = attachment.metadata.get(
                            "ocr_status", "not processed"
                        )
                        ocr_confidence = attachment.metadata.get("ocr_confidence", 0.0)
                        logger.info(f"  - Image: {attachment.path.name}")
                        logger.info(f"    OCR Status: {ocr_status}")
                        logger.info(f"    OCR Confidence: {ocr_confidence:.1f}%")
                    else:
                        logger.info(f"  - File: {attachment.path.name}")
            else:
                logger.info("No attachments")
            logger.info("-" * 50)

    except Exception as e:
        logger.error(f"Error processing notes: {str(e)}", exc_info=True)


def main():
    """Main entry point."""
    # Default paths
    input_dir = Path(
        "/Users/chadwalters/Library/Mobile Documents/com~apple~CloudDocs/_NovaInput"
    )
    nova_dir = Path.home() / ".nova"

    # Ensure directories exist
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        return

    nova_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Processing notes from: {input_dir}")
    logger.info(f"Using .nova directory: {nova_dir}")

    # Run async process
    asyncio.run(process_notes(input_dir, nova_dir))


if __name__ == "__main__":
    main()
