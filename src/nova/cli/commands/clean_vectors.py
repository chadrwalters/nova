"""Clean vectors command."""

import logging
import shutil
from pathlib import Path
from typing import Any

import click

from nova.cli.utils.command import NovaCommand

logger = logging.getLogger(__name__)


class CleanVectorsCommand(NovaCommand):
    """Clean vectors command for nova CLI."""

    name = "clean-vectors"

    def run(self, **kwargs: Any) -> None:
        """Run the clean-vectors command.

        Args:
            **kwargs: Command arguments
        """
        force = kwargs.get("force", False)
        vector_dir = Path(".nova/vectors")

        if not vector_dir.exists():
            logger.info("Vector store directory does not exist")
            return

        if not force:
            logger.warning("Use --force to actually delete the vector store")
            return

        try:
            shutil.rmtree(vector_dir)
            logger.info("Vector store deleted successfully")
        except Exception as e:
            msg = f"Failed to delete vector store: {str(e)}"
            logger.error(msg)
            raise click.Abort(msg) from e

    def create_command(self) -> click.Command:
        """Create the clean-vectors command.

        Returns:
            click.Command: The Click command
        """

        @click.command(name="clean-vectors")
        @click.option(
            "--force",
            is_flag=True,
            help="Force deletion without confirmation",
        )
        def clean_vectors(force: bool) -> None:
            """Clean the vector store.

            This command deletes the vector store directory and all its
            contents. Use with caution as this operation cannot be
            undone.
            """
            self.run(force=force)

        return clean_vectors
