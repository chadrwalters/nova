"""Process notes command."""

import logging
from pathlib import Path

import click

from nova.bear_parser.parser import BearParser
from nova.cli.base import BaseCommand

logger = logging.getLogger(__name__)


class ProcessNotesCommand(BaseCommand):
    """Command for processing notes."""

    def __init__(self) -> None:
        """Initialize command."""
        super().__init__()

    @click.command()
    @click.argument("input_dir", type=click.Path(exists=True, path_type=Path))
    @click.argument("output_dir", type=click.Path(path_type=Path))
    def process_notes(self, input_dir: Path, output_dir: Path) -> None:
        """Process Bear notes from input directory.

        Args:
            input_dir: Input directory containing Bear notes
            output_dir: Output directory for processed notes
        """
        try:
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)

            # Process notes
            parser = BearParser(input_dir)
            notes = parser.process_notes(output_dir)

            logger.info("Processed %d notes", len(notes))

        except Exception as e:
            logger.error("Failed to process notes: %s", e)
            raise click.ClickException(str(e)) from e
