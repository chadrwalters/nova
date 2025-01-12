"""Process notes command."""

import logging
from pathlib import Path
from typing import Any

import click
from rich.console import Console

from nova.cli.utils.command import NovaCommand
from nova.config import load_config
from nova.ingestion.bear import BearParser

logger = logging.getLogger(__name__)


class ProcessNotesCommand(NovaCommand):
    """Process notes command for nova CLI."""

    name = "process-notes"

    def run(self, **kwargs: Any) -> None:
        """Run the process-notes command."""
        config = load_config()
        input_dir = kwargs.get("input_dir")
        output_dir = kwargs.get("output_dir")

        if not input_dir:
            input_dir = str(config.paths.input_dir)
        if not output_dir:
            output_dir = str(config.paths.processing_dir)

        input_path = Path(input_dir)
        output_path = Path(output_dir) if output_dir else None

        if not input_path.exists():
            msg = f"Input directory does not exist: {input_path}"
            logger.error(msg)
            raise click.Abort(msg)

        if output_path:
            output_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Output directory: {output_path}")

        logger.info(f"Processing notes from {input_path}")
        console = Console()
        with console.status("Processing notes..."):
            try:
                parser = BearParser()
                parser.process_notes(
                    str(input_path),
                    str(output_path) if output_path else str(input_path),
                )
                logger.info("SUCCESS: Notes processed successfully!")
            except Exception as e:
                msg = f"Failed to process notes: {str(e)}"
                logger.error(msg)
                raise click.Abort(msg) from e

    def create_command(self) -> click.Command:
        """Create the process-notes command."""

        @click.command(help="Process notes from Bear.app exports.")
        @click.option("--input-dir", help="Directory containing Bear.app note exports.")
        @click.option("--output-dir", help="Directory to save processed notes.")
        def process_notes(input_dir: str | None, output_dir: str | None) -> None:
            self.run(input_dir=input_dir, output_dir=output_dir)

        return process_notes
