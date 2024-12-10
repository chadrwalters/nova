import os
import time
from enum import Enum
from os import PathLike
from pathlib import Path
from typing import List, Optional, Sequence, Union, cast

import click
from dotenv import load_dotenv
from rich.console import Console

from src.core.config import ProcessingConfig
from src.core.document_consolidator import DocumentConsolidator
from src.core.exceptions import PipelineError, ProcessingError
from src.core.logging import get_logger, setup_logging
from src.processors.html_processor import HTMLProcessor
from src.processors.markdown_to_pdf_processor import convert_markdown_to_pdf
from src.resources.templates.template_manager import TemplateManager
from src.utils.colors import NovaConsole

# Set up logging
setup_logging(log_level="INFO", json_format=False)
logger = get_logger(__name__)

nova_console = NovaConsole()

# Initialize console for rich output
console = Console()


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
    """Enum representing different processing phases."""

    INDIVIDUAL_HTML = "individual_html"
    CONSOLIDATED_MARKDOWN = "consolidated_markdown"
    CONSOLIDATED_HTML = "consolidated_html"
    PDF = "pdf"
    ALL = "all"


def load_config() -> ProcessingConfig:
    """Load configuration from environment variables."""
    load_dotenv()

    # Get required paths
    input_dir = os.getenv("NOVA_INPUT_DIR", "")
    output_dir = os.getenv("NOVA_OUTPUT_DIR", "")
    consolidated_dir = os.getenv("NOVA_CONSOLIDATED_DIR", "")
    processing_dir = os.getenv("NOVA_PROCESSING_DIR", "")
    template_dir = os.getenv("NOVA_TEMPLATE_DIR", "")
    media_dir = os.getenv("NOVA_MEDIA_DIR", "")

    if not all([input_dir, output_dir, consolidated_dir]):
        raise ProcessingError("Required environment variables are missing")

    return ProcessingConfig(
        input_dir=Path(input_dir),
        output_dir=Path(output_dir),
        consolidated_dir=Path(consolidated_dir),
        processing_dir=Path(processing_dir) if processing_dir else None,
        template_dir=Path(template_dir) if template_dir else None,
        media_dir=Path(media_dir) if media_dir else None,
    )


def initialize_processor(
    input_dir: Path,
    output_dir: Path,
    consolidated_dir: Path,
    temp_dir: Path,
    template_dir: Path,
    error_tolerance: str = "strict",
) -> DocumentConsolidator:
    """Initialize document processor with configuration.

    Args:
        input_dir: Input directory path
        output_dir: Output directory path
        consolidated_dir: Consolidated files directory path
        temp_dir: Temporary files directory path
        template_dir: Template files directory path
        error_tolerance: Error handling mode ("strict" or "lenient")

    Returns:
        Initialized DocumentConsolidator instance
    """
    return DocumentConsolidator(
        input_dir=input_dir,
        output_dir=output_dir,
        consolidated_dir=consolidated_dir,
        temp_dir=temp_dir,
        template_dir=template_dir,
        error_tolerance=error_tolerance == "lenient",
    )


@click.group()
def cli() -> None:
    """Nova document processing CLI."""
    pass


@cli.command()
@click.option("--force", is_flag=True, help="Force processing of all files")
@click.option(
    "--processing-dir",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    help="Directory for intermediate processing files",
)
@click.option(
    "--phase",
    type=click.Choice([p.name for p in ProcessingPhase], case_sensitive=False),
    default=ProcessingPhase.ALL.name,
    help="Processing phase to execute",
)
def process(
    force: bool,
    processing_dir: Optional[Path] = None,
    phase: str = ProcessingPhase.ALL.name,
) -> None:
    """Process markdown files."""
    console = Console()
    start_time = time.time()
    try:
        # Load configuration
        config = load_config()

        # Update config with command-line processing directory if provided
        if processing_dir:
            config.processing_dir = processing_dir.resolve()
            config.processing_dir.mkdir(parents=True, exist_ok=True)
            (config.processing_dir / "markdown").mkdir(parents=True, exist_ok=True)
            (config.processing_dir / "html").mkdir(parents=True, exist_ok=True)
            (config.processing_dir / "html" / "individual").mkdir(
                parents=True, exist_ok=True
            )
            (config.processing_dir / "attachments").mkdir(parents=True, exist_ok=True)
            (config.processing_dir / "media").mkdir(parents=True, exist_ok=True)

        # Initialize processor
        processor = DocumentConsolidator(
            input_dir=config.input_dir,
            output_dir=config.output_dir,
            consolidated_dir=config.consolidated_dir,
            temp_dir=config.processing_dir or Path("temp"),
            template_dir=config.template_dir or Path("templates"),
            error_tolerance=False,  # Default to strict mode
        )

        # Get input files
        input_files = sorted(config.input_dir.glob("*.md"))
        if not force:
            # Only process files that haven't been processed
            files_to_process = [
                f
                for f in input_files
                if not (
                    config.processing_dir or Path("temp") / "html" / f"{f.stem}.html"
                ).exists()
            ]
        else:
            files_to_process = input_files

        # Process files based on phase
        match ProcessingPhase[phase.upper()]:
            case ProcessingPhase.INDIVIDUAL_HTML:
                processor._process_markdown_files(files_to_process)
            case ProcessingPhase.CONSOLIDATED_MARKDOWN:
                processor.consolidate_files(files_to_process)
            case ProcessingPhase.CONSOLIDATED_HTML:
                processor.consolidate_files(files_to_process)
            case ProcessingPhase.PDF:
                processor.consolidate_files(files_to_process)
            case ProcessingPhase.ALL:
                processor.consolidate_files(files_to_process)

        # Print completion message
        duration = time.time() - start_time
        console.print(f"\nTotal processing time: {format_time(duration)}")

    except Exception as err:
        console.print(f"[red]Error: {str(err)}[/red]")
        raise click.Abort() from err


@cli.command()
def clean() -> None:
    """Clean temporary files and directories."""
    try:
        config = load_config()
        processing_dir = config.processing_dir

        # Clean processing directory
        if processing_dir and processing_dir.exists():
            for item in processing_dir.glob("*"):
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    import shutil

                    shutil.rmtree(item)

        print(click.style("Cleaned temporary files", fg="green"))

    except Exception as err:
        print(click.style(f"Cleanup failed: {str(err)}", fg="red"))
        raise click.ClickException(str(err)) from err


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
) -> None:
    """Convert markdown files to HTML."""
    try:
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize processor
        processor = HTMLProcessor(template_dir=template_dir, temp_dir=output_dir)

        # Get markdown files
        pattern = "**/*.md" if recursive else "*.md"
        markdown_files = sorted(input_dir.glob(pattern))

        if not markdown_files:
            print(click.style("No markdown files found", fg="yellow"))
            return

        # Process each file
        for md_file in markdown_files:
            print(click.style(f"Converting {md_file} to HTML", fg="cyan"))
            processor.convert_to_html(str(md_file), output_dir)

        print(click.style("HTML conversion complete", fg="green"))

    except Exception as err:
        print(click.style(f"HTML conversion failed: {str(err)}", fg="red"))
        raise click.ClickException(f"HTML conversion failed: {str(err)}") from err


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
def html_consolidate(input_dir: Path, output_file: Path, template_dir: Path) -> None:
    """Consolidate HTML files into a single file."""
    try:
        # Initialize processor
        processor = HTMLProcessor(
            template_dir=template_dir, temp_dir=output_file.parent
        )

        # Get HTML files
        html_files = sorted(input_dir.glob("*.html"))

        if not html_files:
            print(click.style("No HTML files found", fg="yellow"))
            return

        # Create output directory if needed
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Consolidate files
        processor.consolidate_html_files(html_files, output_file)

        print(click.style("HTML consolidation complete", fg="green"))

    except Exception as err:
        print(click.style(f"HTML consolidation failed: {str(err)}", fg="red"))
        raise click.ClickException(f"HTML consolidation failed: {str(err)}") from err


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
    "--processing-dir",
    "-d",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    help="Processing directory",
)
def pdf(
    input_file: Path,
    output_file: Path,
    media_dir: Path,
    template_dir: Path,
    processing_dir: Optional[Path] = None,
) -> None:
    """Convert markdown file to PDF."""
    try:
        nova_console.process_item(f"Converting {input_file} to PDF")
        convert_markdown_to_pdf(
            input_file,
            output_file,
            media_dir=media_dir,
            template_dir=template_dir,
            processing_dir=processing_dir,
        )
        nova_console.success(f"Successfully created PDF: {output_file}")
    except Exception as err:
        print(click.style(f"Failed to create PDF: {str(err)}", fg="red"))
        raise click.ClickException(str(err)) from err


def validate_paths(
    input_dir: Optional[str],
    output_dir: Optional[str],
    consolidated_dir: Optional[str],
    temp_dir: Optional[str],
    template_dir: Optional[str],
) -> tuple[Path, Path, Path, Path, Path]:
    """Validate and convert path strings to Path objects.

    Args:
        input_dir: Input directory path
        output_dir: Output directory path
        consolidated_dir: Consolidated files directory path
        temp_dir: Temporary files directory path
        template_dir: Template files directory path

    Returns:
        Tuple of validated Path objects

    Raises:
        ProcessingError: If any required path is missing or invalid
    """
    if not all([input_dir, output_dir, consolidated_dir, temp_dir, template_dir]):
        raise ProcessingError("All directory paths must be provided")

    try:
        paths = (
            Path(cast(str, input_dir)),
            Path(cast(str, output_dir)),
            Path(cast(str, consolidated_dir)),
            Path(cast(str, temp_dir)),
            Path(cast(str, template_dir)),
        )

        # Create directories if they don't exist
        for path in paths[1:]:  # Skip input_dir as it must exist
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as err:
                raise ProcessingError(f"Failed to create directory: {path}") from err

        return paths

    except ProcessingError:
        raise  # Re-raise ProcessingError with its original context
    except Exception as err:
        raise ProcessingError("Failed to create path objects") from err


@cli.command()
@click.option(
    "--input-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="Directory containing input markdown files",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="Directory for output files",
)
@click.option(
    "--processing-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="Directory for processing files",
)
@click.option(
    "--template-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="Directory containing HTML templates",
)
def consolidate(
    input_dir: Path,
    output_dir: Path,
    processing_dir: Path,
    template_dir: Path,
) -> None:
    """Consolidate markdown files into a single document."""
    try:
        # Create config from CLI arguments
        config = ProcessingConfig(
            input_dir=input_dir,
            output_dir=output_dir,
            processing_dir=processing_dir,
        )

        # Initialize processor with config
        processor = DocumentConsolidator(
            config=config,
            error_tolerance=False,  # Default to strict mode
        )

        # Get input files
        input_files = sorted(input_dir.glob("*.md"))
        if not input_files:
            logger.warning(f"No markdown files found in {input_dir}")
            return

        # Process files
        processor.consolidate_files(input_files)

    except Exception as err:
        logger.error("Error during consolidation", exc_info=err)
        raise click.Abort() from err


# Add commands to CLI group
cli.add_command(html_convert)
cli.add_command(html_consolidate)
cli.add_command(pdf)
cli.add_command(consolidate)

if __name__ == "__main__":
    cli()
