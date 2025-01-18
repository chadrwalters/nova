"""Process notes command."""

import logging
from pathlib import Path
from typing import Any

import click

from nova.bear_parser.processing import BearNoteProcessing
from nova.cli.utils.command import NovaCommand
from nova.cli.utils.errors import RebuildErrorType, create_rebuild_error
from nova.config import load_config
from nova.monitoring.session import SessionMonitor

logger = logging.getLogger(__name__)


class ProcessNotesCommand(NovaCommand):
    """Command for processing notes."""

    name = "process-notes"
    help = "Process notes from input directory"

    def run(self, **kwargs: Any) -> None:
        """Run the process notes command.

        Args:
            **kwargs: Command arguments
        """
        # Load config for default paths
        config = load_config()

        # Get input directory
        input_dir = (
            Path(kwargs.get("input_dir", "")) if kwargs.get("input_dir") else config.paths.input_dir
        )

        # Get output directory
        output_dir = (
            Path(kwargs.get("output_dir", ""))
            if kwargs.get("output_dir")
            else config.paths.processing_dir
        )

        if not input_dir.exists():
            error = create_rebuild_error(
                error_type=RebuildErrorType.INITIALIZATION,
                message=f"Input directory not found: {input_dir}",
                context={"input_dir": str(input_dir)},
                is_recoverable=True,
                recovery_hint="Check input directory path and retry",
            )
            self.handle_error(error)
            raise click.UsageError(f"Input directory not found: {input_dir}")

        # Initialize monitoring
        monitor = SessionMonitor(nova_dir=config.paths.state_dir)

        try:
            # Process notes using BearNoteProcessing
            processor = BearNoteProcessing(input_dir=input_dir, output_dir=output_dir)
            documents = processor.process_bear_notes()

            # Update monitoring
            monitor.track_rebuild_progress(total_chunks=len(documents))
            for i in range(len(documents)):
                monitor.update_rebuild_progress(chunks_processed=i + 1, processing_time=0.1)
            monitor.complete_rebuild()

            self.log_success(f"Processed {len(documents)} notes from {input_dir} to {output_dir}")
        except Exception as e:
            error = create_rebuild_error(
                error_type=RebuildErrorType.PROCESSING,
                message=str(e),
                context={"input_dir": str(input_dir), "output_dir": str(output_dir)},
                is_recoverable=True,
                recovery_hint="Check input files and retry",
            )
            monitor.record_rebuild_error(str(error))
            self.handle_error(error)
            raise click.UsageError(f"Failed to process notes: {e}")

    def create_command(self) -> click.Command:
        """Create the process notes command.

        Returns:
            The click command instance
        """

        @click.command(name=self.name, help=self.help)
        @click.option(
            "--input-dir",
            type=click.Path(path_type=Path),
            required=False,
            help="Input directory path (default: from config)",
        )
        @click.option(
            "--output-dir",
            type=click.Path(path_type=Path),
            default=None,
            help="Output directory path (default: .nova/processing)",
        )
        def command(**kwargs: Any) -> None:
            """Process notes from input directory.

            Args:
                **kwargs: Command arguments
            """
            self.run(**kwargs)

        return command
