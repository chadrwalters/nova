"""Process notes command."""

import logging
from pathlib import Path
from typing import Any

import click

from nova.cli.utils.command import NovaCommand
from nova.ingestion.bear import process_note


logger = logging.getLogger(__name__)


class ProcessNotesCommand(NovaCommand):
    """Command for processing notes."""

    def run(self, **kwargs: Any) -> None:
        """Run the command.

        Args:
            **kwargs: Command arguments
        """
        input_dir = kwargs["input_dir"]
        output_dir = kwargs["output_dir"]

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        try:
            # Process all notes in input directory
            input_path = Path(input_dir)
            note_files = list(input_path.glob("*.txt"))
            if not note_files:
                logger.warning(f"No note files found in {input_dir}")
                return

            # Process each note
            for note_file in note_files:
                try:
                    chunks = process_note(note_file, output_path)
                    logger.info(f"Processed {note_file} into {len(chunks)} chunks")
                except Exception as e:
                    logger.error(f"Failed to process note {note_file}: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Failed to process notes: {str(e)}")
            raise click.Abort()

    def create_command(self) -> click.Command:
        """Create the command.

        Returns:
            Click command object
        """

        @click.command(name="process-notes")
        @click.option(
            "--input-dir", required=True, help="Input directory containing notes"
        )
        @click.option(
            "--output-dir", required=True, help="Output directory for processed notes"
        )
        def command(input_dir: str, output_dir: str) -> None:
            """Process notes into chunks."""
            self.run(input_dir=input_dir, output_dir=output_dir)

        return command


if __name__ == "__main__":
    command = ProcessNotesCommand()
    command.create_command()()
