"""Command line interface for Nova."""

import click
from pathlib import Path
from .frontend.build import build_frontend

@click.group()
def cli():
    """Nova CLI."""
    pass

@cli.command()
def build():
    """Build Nova frontend."""
    try:
        build_frontend()
        click.echo("Frontend built successfully!")
    except Exception as e:
        click.echo(f"Error building frontend: {e}", err=True)
        raise click.Abort()

def main():
    """Main entry point."""
    cli()

if __name__ == '__main__':
    main() 