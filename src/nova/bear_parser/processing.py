"""Bear note processing module."""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .parser import BearNote, BearParser, BearDocument, InputFormat

logger = logging.getLogger(__name__)


class BearNoteProcessing:
    """Unified Bear note processing class."""

    def __init__(self, input_dir: str | Path, output_dir: Optional[str | Path] = None) -> None:
        """Initialize Bear note processor.

        Args:
            input_dir: Input directory containing Bear notes
            output_dir: Optional output directory for processed notes
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir) if output_dir else None
        self.parser = BearParser(input_dir=self.input_dir)

    def process_bear_notes(self) -> List[BearDocument]:
        """Process all Bear notes in the input directory.

        Returns:
            List of processed BearDocument instances

        Raises:
            BearParserError: If processing fails
        """
        logger.info("Processing Bear notes from %s", self.input_dir)

        # Parse and process notes
        self.parser.parse_directory()
        documents = self.parser.process_notes()

        # Copy files to output directory if specified
        if self.output_dir:
            self._copy_files_to_output()

        logger.info("Successfully processed %d notes", len(documents))
        return documents

    def _copy_files_to_output(self) -> None:
        """Copy note files to output directory."""
        if not self.output_dir:
            return

        try:
            # Create output directory
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Copy markdown and text files
            for ext in [".md", ".txt"]:
                for file_path in self.input_dir.glob(f"*{ext}"):
                    try:
                        # Create relative path in output directory
                        rel_path = file_path.relative_to(self.input_dir)
                        output_path = self.output_dir / rel_path
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(file_path, output_path)
                        logger.debug("Copied %s to %s", file_path, output_path)
                    except Exception as e:
                        logger.error("Failed to copy file %s: %s", file_path, e)
                        continue

            # Copy attachments if present
            for attachment_dir in self.input_dir.glob("*"):
                if attachment_dir.is_dir():
                    try:
                        # Copy entire attachment directory
                        output_attachment_dir = self.output_dir / attachment_dir.name
                        shutil.copytree(attachment_dir, output_attachment_dir, dirs_exist_ok=True)
                        logger.debug("Copied attachments from %s to %s", attachment_dir, output_attachment_dir)
                    except Exception as e:
                        logger.error("Failed to copy attachments from %s: %s", attachment_dir, e)
                        continue
        except Exception as e:
            logger.error("Failed to create output directory %s: %s", self.output_dir, e)
