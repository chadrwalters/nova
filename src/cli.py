#!/usr/bin/env python3

from pathlib import Path

import typer

from src.core.markdown_consolidator import consolidate
from src.core.markdown_to_pdf_converter import convert_markdown_to_pdf
from src.utils.colors import NovaConsole

# Initialize console
nova_console = NovaConsole()

# Initialize typer app
app = typer.Typer()


@app.command()
def consolidate_cmd(
    input_dir: str = typer.Argument(
        ..., help="Input directory containing markdown files"
    ),
    output_file: str = typer.Argument(..., help="Output consolidated markdown file"),
    media_dir: str = typer.Option("_media", help="Media directory for images"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Process subdirectories recursively"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose output"),
) -> None:
    """Consolidate multiple markdown files into a single file."""
    try:
        input_path = Path(input_dir)
        output_path = Path(output_file)
        media_path = Path(media_dir)

        # Create media directory if it doesn't exist
        media_path.mkdir(parents=True, exist_ok=True)

        nova_console.process_item(f"Consolidating markdown files from {input_path}")
        consolidate(input_path, output_path, recursive=recursive, verbose=verbose)
        nova_console.success(f"Successfully consolidated files to {output_path}")

    except Exception as e:
        nova_console.error(f"Failed to consolidate files: {str(e)}")
        raise typer.Exit(1)


@app.command()
def pdf(
    input_file: str = typer.Argument(..., help="Input markdown file"),
    output_file: str = typer.Argument(..., help="Output PDF file"),
    media_dir: str = typer.Option("_media", help="Media directory for images"),
    template_dir: str = typer.Option(
        "src/resources/templates", help="Template directory"
    ),
    debug_dir: str = typer.Option(
        None, help="Debug output directory for intermediate files"
    ),
) -> None:
    """Convert markdown file to PDF."""
    try:
        input_path = Path(input_file)
        output_path = Path(output_file)
        media_path = Path(media_dir) if media_dir else None
        template_path = Path(template_dir) if template_dir else None
        debug_path = Path(debug_dir) if debug_dir else None

        nova_console.process_item(f"Converting {input_path} to PDF")
        convert_markdown_to_pdf(
            input_path,
            output_path,
            media_dir=media_path,
            template_dir=template_path,
            debug_dir=debug_path
        )
        nova_console.success(f"Successfully created PDF: {output_path}")

    except Exception as e:
        nova_console.error(f"Failed to create PDF: {str(e)}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
