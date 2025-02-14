"""Clean processing command."""

import asyncio
import logging
import shutil
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os
import click

from nova.cli.utils.command import NovaCommand

logger = logging.getLogger(__name__)


class CleanProcessingCommand(NovaCommand):
    """Clean processing command for nova CLI."""

    name = "clean-processing"
    help = "Clean the processing directory"

    async def run_async(self, **kwargs: Any) -> None:
        """Run the clean-processing command asynchronously.

        Args:
            **kwargs: Command arguments
        """
        force = kwargs.get("force", False)
        processing_dir = Path(".nova/processing")

        if not await aiofiles.os.path.exists(str(processing_dir)):
            self.log_info("Processing directory does not exist")
            return

        if not force:
            self.log_warning("Use --force to actually delete the processing directory")
            return

        try:
            # Run rmtree in a thread to avoid blocking
            await asyncio.to_thread(shutil.rmtree, processing_dir)
            self.log_info("Processing directory deleted successfully")

        except PermissionError as e:
            msg = f"Failed to delete processing directory: {e}"
            self.log_error(msg)
            raise click.Abort(msg)
        except Exception as e:
            msg = f"Failed to delete processing directory: {e}"
            self.log_error(msg)
            raise click.Abort(msg)

    def run(self, **kwargs: Any) -> None:
        """Run the command.

        Args:
            **kwargs: Command arguments
        """
        asyncio.run(self.run_async(**kwargs))

    def create_command(self) -> click.Command:
        """Create the clean-processing command.

        Returns:
            click.Command: The Click command
        """

        @click.command(name="clean-processing")
        @click.option(
            "--force",
            is_flag=True,
            help="Force deletion without confirmation",
        )
        def clean_processing(force: bool) -> None:
            """Clean the processing directory.

            This command deletes the processing directory and all its
            contents. Use with caution as this operation cannot be
            undone.
            """
            self.run(force=force)

        return clean_processing
