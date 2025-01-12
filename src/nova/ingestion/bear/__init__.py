"""Bear note ingestion module."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


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

        note_files = list(input_path.glob("*.txt"))
        if not note_files:
            logger.warning("No note files found in %s", input_dir)
            return

        for note_file in note_files:
            try:
                process_note(note_file, output_path)
                logger.info("Processed note: %s", note_file.name)
            except Exception as e:
                logger.error("Failed to process note %s: %s", note_file.name, e)
                raise


def process_note(note_file: Path, output_dir: Path | None = None) -> list[str]:
    """Process a Bear note file.

    Args:
        note_file: Path to the note file
        output_dir: Optional output directory for processed note

    Returns:
        List[str]: List of chunks from the note

    Raises:
        Exception: If note processing fails
    """
    try:
        with open(note_file, encoding="utf-8") as f:
            content = f.read()

        chunks = []
        for line in content.split("\n"):
            if line.strip():
                chunks.append(line.strip())

        if output_dir:
            output_file = output_dir / note_file.name
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("\n".join(chunks))

        return chunks
    except Exception as e:
        logger.error("Failed to process note %s: %s", note_file.name, e)
        raise
