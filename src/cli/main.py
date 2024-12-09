import os
import time
from enum import Enum, auto
from pathlib import Path
from typing import Optional

import click
import structlog
from dotenv import load_dotenv

from src.core.config import ProcessingConfig
from src.core.document_consolidator import DocumentConsolidator
from src.core.exceptions import ProcessingError
from src.core.markdown_to_pdf_converter import convert_markdown_to_pdf
from src.core.types import ProcessingPhase
from src.utils.colors import NovaConsole

logger = structlog.get_logger(__name__)

nova_console = NovaConsole()


def format_time(seconds: float) -> str:
    """Format time duration in a human-readable way."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    seconds = seconds % 60
    return f"{minutes}m {seconds:.1f}s"


def shorten_path(path: str) -> str:
    """Shorten a path for display by showing only the filename."""
    return Path(path).name


class ProcessingPhase(Enum):
    """Processing phases for document consolidation."""

    HTML_INDIVIDUAL = auto()  # Generate individual HTML files only
    MARKDOWN_CONSOLIDATED = auto()  # Generate consolidated markdown
    HTML_CONSOLIDATED = auto()  # Generate consolidated HTML
    PDF = auto()  # Generate final PDF
    ALL = auto()  # Complete processing (default)


def load_config() -> ProcessingConfig:
    """Load configuration from environment variables."""
    load_dotenv()

    # Load paths from environment
    base_dir = Path(os.getenv("NOVA_INPUT_DIR"))
    output_dir = Path(os.getenv("NOVA_CONSOLIDATED_DIR"))
    template_dir = Path(os.getenv("NOVA_TEMPLATE_DIR", "src/resources/templates"))
    media_dir = Path(os.getenv("NOVA_MEDIA_DIR"))
    debug_dir = (
        Path(os.getenv("NOVA_DEBUG_DIR")) if os.getenv("NOVA_DEBUG_DIR") else None
    )

    # Create configuration
    return ProcessingConfig(
        template_dir=template_dir,
        media_dir=media_dir,
        relative_media_path="../_media",  # Default for individual files
        debug_dir=debug_dir,
        error_tolerance=os.getenv("NOVA_ERROR_TOLERANCE", "lenient"),
    )


@click.group()
def cli():
    """Nova - Markdown Document Consolidation Tool"""
    pass


@cli.command()
@click.option("--force", is_flag=True, help="Force reprocessing of all documents")
@click.option(
    "--debug-dir", type=click.Path(path_type=Path), help="Debug output directory"
)
@click.option(
    "--phase",
    type=click.Choice([phase.name for phase in ProcessingPhase], case_sensitive=False),
    default=ProcessingPhase.ALL.name,
    help="Stop processing at specified phase",
)
def process(
    force: bool, debug_dir: Optional[Path] = None, phase: str = ProcessingPhase.ALL.name
) -> None:
    """Process markdown files."""
    try:
        # Create required directories
        template_dir = Path("templates")
        template_dir.mkdir(parents=True, exist_ok=True)

        media_dir = Path("media")
        media_dir.mkdir(parents=True, exist_ok=True)

        # Initialize configuration
        config = ProcessingConfig(
            template_dir=template_dir,
            media_dir=media_dir,
            relative_media_path="_media",
            debug_dir=debug_dir.resolve() if debug_dir else None,
            error_tolerance="lenient",
        )

        # Get input files
        input_dir = Path(
            "/Users/ChadWalters/Library/Mobile Documents/com~apple~CloudDocs/_NovaIndividualMarkdown"
        )
        output_dir = Path(
            "/Users/ChadWalters/Library/Mobile Documents/com~apple~CloudDocs/_Nova"
        )

        # Initialize processors
        consolidator = DocumentConsolidator(
            base_dir=input_dir, output_dir=output_dir, config=config
        )

        # Log with shortened paths
        print()  # Add blank line
        print(click.style(f"Starting {phase} processing...", fg="cyan"))
        print()  # Add blank line

        # Get input files
        input_files = (
            sorted(input_dir.glob("**/*.md"))
            if force
            else [
                f
                for f in input_dir.glob("**/*.md")
                if not (debug_dir / "html" / f"{f.stem}.html").exists()
            ]
        )

        # Log input files with shortened paths
        if input_files:
            print(click.style(f"Found {len(input_files)} files to process:", fg="cyan"))
            print()
            for f in input_files:
                print(f"  • {f.name}")
            print()
        else:
            print(click.style("No files to process", fg="yellow"))
            return

        # Process files
        print(click.style("Phase 1: Generating individual HTML files...", fg="cyan"))
        start_time = time.time()

        # Process files
        result = consolidator.consolidate_documents(
            input_files, "Consolidated Document"
        )

        # Log warnings
        if result.warnings:
            print()
            print(click.style("Warnings:", fg="yellow"))
            for warning in result.warnings:
                print(f"  • {warning}")
            print()

        # Log completion
        elapsed = time.time() - start_time
        print(
            click.style(
                f"✓ Individual HTML files generated ({elapsed:.1f}s)", fg="green"
            )
        )
        print()

        # Stop if requested
        if phase == ProcessingPhase.HTML_INDIVIDUAL.name:
            return

        # Generate consolidated markdown
        print(click.style("Phase 2: Generating consolidated markdown...", fg="cyan"))
        start_time = time.time()

        # Create consolidated markdown directory
        consolidated_dir = Path(
            "/Users/ChadWalters/Library/Mobile Documents/com~apple~CloudDocs/_NovaConsolidatedMarkdown"
        )
        consolidated_dir.mkdir(parents=True, exist_ok=True)

        # Write consolidated markdown
        consolidated_md = consolidated_dir / "consolidated.md"
        consolidated_md.write_text(result.content)

        # Log completion
        elapsed = time.time() - start_time
        print(
            click.style(
                f"✓ Consolidated markdown generated ({elapsed:.1f}s)", fg="green"
            )
        )
        print()

        # Stop if requested
        if phase == ProcessingPhase.MARKDOWN_CONSOLIDATED.name:
            return

        # Generate consolidated HTML
        print(click.style("Phase 3: Generating consolidated HTML...", fg="cyan"))
        start_time = time.time()

        # Write consolidated HTML
        consolidated_html = consolidated_dir / "consolidated.html"
        if (
            result.consolidated_html
            and result.consolidated_html.exists()
            and not result.consolidated_html.is_dir()
        ):
            consolidated_html.write_text(result.consolidated_html.read_text())
            logger.info(f"Generated consolidated HTML: {consolidated_html}")
        else:
            error_msg = "No valid consolidated HTML file was generated"
            logger.error(error_msg)
            raise ProcessingError(error_msg)

        # Log completion
        elapsed = time.time() - start_time
        print(
            click.style(f"✓ Consolidated HTML generated ({elapsed:.1f}s)", fg="green")
        )
        print()

        # Stop if requested
        if phase == ProcessingPhase.HTML_CONSOLIDATED.name:
            return

        # Generate PDF
        print(click.style("Phase 4: Generating PDF...", fg="cyan"))
        start_time = time.time()

        # Create PDF directory
        pdf_dir = output_dir / "pdf"
        pdf_dir.mkdir(parents=True, exist_ok=True)

        # Generate PDF
        pdf_file = pdf_dir / "consolidated.pdf"
        try:
            import shutil
            import subprocess
            import tempfile

            # Create temporary directory for processing
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_html = Path(temp_dir) / "input.html"
                temp_pdf = Path(temp_dir) / "output.pdf"

                # Copy HTML file to temp directory
                shutil.copy2(consolidated_html, temp_html)

                # Run wkhtmltopdf with minimal options
                cmd = [
                    "wkhtmltopdf",
                    "--enable-local-file-access",
                    "--disable-smart-shrinking",
                    "--print-media-type",
                    "--page-size",
                    "Letter",
                    "--margin-top",
                    "25.4",
                    "--margin-right",
                    "25.4",
                    "--margin-bottom",
                    "25.4",
                    "--margin-left",
                    "25.4",
                    str(temp_html),
                    str(temp_pdf),
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode != 0:
                    print(
                        click.style(
                            f"Failed to generate PDF: {result.stderr}", fg="red"
                        )
                    )
                    return

                # Copy PDF back if successful
                if temp_pdf.exists() and temp_pdf.stat().st_size > 0:
                    shutil.copy2(temp_pdf, pdf_file)
                else:
                    print(
                        click.style(
                            "Generated PDF file is empty or not created", fg="red"
                        )
                    )
                    return

        except Exception as e:
            print(click.style(f"Failed to generate PDF: {str(e)}", fg="red"))
            if pdf_file.exists():
                pdf_file.unlink()  # Clean up failed PDF
            return

        # Log completion
        elapsed = time.time() - start_time
        print(click.style(f"✓ PDF generated ({elapsed:.1f}s)", fg="green"))
        print()

        # Log total time
        total_elapsed = time.time() - start_time
        print(click.style(f"Total processing time: {total_elapsed:.1f}s", fg="green"))
        print()

        # Log generated files
        print(click.style("✓ Generated consolidated markdown:", fg="green"))
        print(f"  📄 {consolidated_md.name}")
        print()

        print(click.style("✓ Generated consolidated HTML:", fg="green"))
        print(f"  📄 {consolidated_html.name}")
        print()

        if phase == ProcessingPhase.ALL.name:
            print(click.style("✓ Generated PDF:", fg="green"))
            print(f"  📄 {pdf_file.name}")
            print()

    except Exception as e:
        print(click.style(f"Error: {str(e)}", fg="red"))
        raise


@cli.command()
def clean():
    """Clean temporary files and directories."""
    try:
        config = load_config()

        # Clean temp directory
        if config["temp_dir"].exists():
            for item in config["temp_dir"].glob("*"):
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    import shutil

                    shutil.rmtree(item)

        print(click.style("Cleaned temporary files", fg="green"))

    except Exception as e:
        print(click.style(f"Cleanup failed: {str(e)}", fg="red"))
        raise click.ClickException(str(e))


@click.command()
@click.argument(
    "input_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.argument(
    "output_dir", type=click.Path(file_okay=False, dir_okay=True, path_type=Path)
)
@click.option(
    "--template-dir",
    "-t",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path("src/resources/templates"),
    help="Directory containing HTML templates",
)
@click.option(
    "--recursive", "-r", is_flag=True, help="Process subdirectories recursively"
)
def html_convert(
    input_dir: Path, output_dir: Path, template_dir: Path, recursive: bool
):
    """Convert markdown files to HTML."""
    try:
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize processor
        processor = HTMLProcessor(template_dir)

        # Get markdown files
        pattern = "**/*.md" if recursive else "*.md"
        markdown_files = sorted(input_dir.glob(pattern))

        if not markdown_files:
            print(click.style("No markdown files found", fg="yellow"))
            return

        # Process each file
        for md_file in markdown_files:
            print(click.style(f"Converting {md_file} to HTML", fg="cyan"))
            processor.markdown_to_html(md_file, output_dir)

        print(click.style("HTML conversion complete", fg="green"))

    except Exception as e:
        print(click.style(f"HTML conversion failed: {str(e)}", fg="red"))
        raise click.ClickException(f"HTML conversion failed: {str(e)}")


@click.command()
@click.argument(
    "input_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.argument(
    "output_file", type=click.Path(file_okay=True, dir_okay=False, path_type=Path)
)
@click.option(
    "--template-dir",
    "-t",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path("src/resources/templates"),
    help="Directory containing HTML templates",
)
def html_consolidate(input_dir: Path, output_file: Path, template_dir: Path):
    """Consolidate HTML files into a single file."""
    try:
        # Initialize processor
        processor = HTMLProcessor(template_dir)

        # Get HTML files
        html_files = sorted(input_dir.glob("*.html"))

        if not html_files:
            print(click.style("No HTML files found", fg="yellow"))
            return

        # Create output directory if needed
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Consolidate files
        processor.consolidate_html(html_files, output_file)

        print(click.style("HTML consolidation complete", fg="green"))

    except Exception as e:
        print(click.style(f"HTML consolidation failed: {str(e)}", fg="red"))
        raise click.ClickException(f"HTML consolidation failed: {str(e)}")


@cli.command()
@click.argument(
    "input_file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
)
@click.argument(
    "output_file", type=click.Path(file_okay=True, dir_okay=False, path_type=Path)
)
@click.option(
    "--media-dir",
    "-m",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path("_media"),
    help="Media directory for images",
)
@click.option(
    "--template-dir",
    "-t",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path("src/resources/templates"),
    help="Template directory",
)
@click.option(
    "--debug-dir",
    "-d",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    help="Debug output directory",
)
def pdf(
    input_file: Path,
    output_file: Path,
    media_dir: Path,
    template_dir: Path,
    debug_dir: Optional[Path] = None,
) -> None:
    """Convert markdown file to PDF."""
    try:
        nova_console.process_item(f"Converting {input_file} to PDF")
        convert_markdown_to_pdf(
            input_file,
            output_file,
            media_dir=media_dir,
            template_dir=template_dir,
            debug_dir=debug_dir,
        )
        nova_console.success(f"Successfully created PDF: {output_file}")
    except Exception as e:
        print(click.style(f"Failed to create PDF: {str(e)}", fg="red"))
        raise click.ClickException(str(e))


# Add commands to CLI group
cli.add_command(html_convert)
cli.add_command(html_consolidate)
cli.add_command(pdf)

if __name__ == "__main__":
    cli()
