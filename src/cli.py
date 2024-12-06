#!/usr/bin/env python3

import typer
from pathlib import Path
from src.core.markdown_consolidator import consolidate_markdown_files
from src.core.markdown_to_pdf_converter import convert_markdown_to_pdf
from src.utils.colors import NovaConsole

# Initialize console
nova_console = NovaConsole()

# Initialize typer app
app = typer.Typer()

@app.command()
def consolidate(
    input_dir: str = typer.Argument(..., help="Input directory containing markdown files"),
    output_file: str = typer.Argument(..., help="Output consolidated markdown file"),
    media_dir: str = typer.Option("_media", help="Media directory for images"),
) -> None:
    """Consolidate multiple markdown files into a single file."""
    try:
        input_path = Path(input_dir)
        output_path = Path(output_file)
        media_path = Path(media_dir)

        # Create media directory if it doesn't exist
        media_path.mkdir(parents=True, exist_ok=True)

        nova_console.process_item(f"Consolidating markdown files from {input_path}")
        consolidate_markdown_files(input_path, output_path, media_path)
        nova_console.success(f"Successfully consolidated files to {output_path}")

    except Exception as e:
        nova_console.error(f"Failed to consolidate files: {str(e)}")
        raise

@app.command()
def pdf(
    input_file: str = typer.Argument(..., help="Input markdown file"),
    output_file: str = typer.Argument(..., help="Output PDF file"),
    media_dir: str = typer.Option("_media", help="Media directory for images"),
    template_dir: str = typer.Option("src/resources/templates", help="Template directory"),
) -> None:
    """Convert markdown file to PDF."""
    try:
        input_path = Path(input_file)
        output_path = Path(output_file)
        media_path = Path(media_dir)
        template_path = Path(template_dir)

        nova_console.process_item(f"Converting {input_path} to PDF")
        convert_markdown_to_pdf(
            str(input_path),
            str(output_path),
            str(media_path),
            str(template_path)
        )
        nova_console.success(f"Successfully created PDF: {output_path}")

    except Exception as e:
        nova_console.error(f"Failed to create PDF: {str(e)}")
        raise

if __name__ == "__main__":
    app() 