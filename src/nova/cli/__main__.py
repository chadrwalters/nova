"""Main entry point for the Nova CLI."""

import click
from .commands.cleanup import cleanup
from .commands.consolidate import consolidate

@click.group()
def cli():
    """Nova document processor CLI."""
    pass

# Add commands
cli.add_command(cleanup)
cli.add_command(consolidate)

if __name__ == '__main__':
    cli() 