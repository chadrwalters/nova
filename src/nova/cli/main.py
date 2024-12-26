"""Nova CLI main entry point."""

import click
from .commands.process import process
from .commands.cleanup import cleanup

@click.group()
def cli():
    """Nova document processor CLI."""
    pass

cli.add_command(process)
cli.add_command(cleanup)

if __name__ == '__main__':
    cli() 