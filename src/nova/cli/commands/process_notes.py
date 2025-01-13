"""Process notes command."""

import logging
from pathlib import Path
from typing import Any

import click

from nova.bear_parser.parser import BearParser
from nova.cli.utils.command import NovaCommand

logger = logging.getLogger(__name__)


class ProcessNotesCommand(NovaCommand):
    """Process notes command."""

    name = "process-notes"
    help = "Process Bear notes from input directory"

    def run(self, **kwargs: Any) -> None:
        """Run the command.

        Args:
            **kwargs: Command arguments
        """
        input_dir = kwargs["input_dir"]
        output_dir = kwargs["output_dir"]

        try:
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)

            # Process notes
            parser = BearParser(input_dir)
            notes = parser.process_notes(output_dir)

            self.log_success(f"Processed {len(notes)} notes")

        except Exception as e:
            self.log_error(f"Failed to process notes: {e}")
            raise click.ClickException(str(e)) from e

    def create_command(self) -> click.Command:
        """Create the click command.

        Returns:
            The click command instance
        """

        @click.command(name=self.name, help=self.help)
        @click.argument("input_dir", type=click.Path(exists=True, path_type=Path))
        @click.argument("output_dir", type=click.Path(path_type=Path))
        def command(input_dir: Path, output_dir: Path) -> None:
            self.run(input_dir=input_dir, output_dir=output_dir)

        return command
