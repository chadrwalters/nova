"""Process notes command implementation."""

import click
from pathlib import Path
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.console import Console
import logging
from typing import Any, Optional, Dict, cast, List
import asyncio
import aiofiles
import aiofiles.os
import os

from nova.cli.utils.command import NovaCommand
from nova.docling import Document, DocumentConverter, FormatDetector, InputFormat
from nova.config import load_config

logger = logging.getLogger(__name__)
console = Console()


class ProcessNotesCommand(NovaCommand):
    """Command for processing notes with format detection."""

    name = "process-notes"

    async def run_async(self, **kwargs: Any) -> None:
        """Run the command asynchronously.

        Args:
            **kwargs: Command arguments
        """
        input_dir = kwargs.get("input_dir")
        output_dir = kwargs.get("output_dir")

        config = load_config()

        # Use default paths if not specified
        input_dir = input_dir or config.paths.input_dir
        output_dir = output_dir or config.paths.processing_dir

        # Create output directory
        await aiofiles.os.makedirs(str(output_dir), exist_ok=True)

        # Initialize format detector and converter
        detector = FormatDetector()
        converter = DocumentConverter()

        # Get all files in input directory
        files: List[Path] = []
        for root, _, filenames in os.walk(str(input_dir)):
            for filename in filenames:
                files.append(Path(root) / filename)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Detect formats
            progress.add_task("Detecting file formats...", total=None)
            formats: Dict[Path, InputFormat] = {}

            async def detect_format(file: Path) -> None:
                try:
                    detected_format = detector.detect_format(file)
                    if detected_format is not None:
                        formats[file] = detected_format
                except Exception as e:
                    logger.error(f"Failed to detect format for {file}: {e}")

            # Run format detection concurrently
            await asyncio.gather(*[detect_format(file) for file in files])

            # Report detected formats
            format_counts: Dict[str, int] = {}
            for fmt in formats.values():
                format_counts[fmt.name] = format_counts.get(fmt.name, 0) + 1

            console.print("\nDetected formats:")
            for format_name, count in format_counts.items():
                console.print(f"  {format_name}: {count} files")

            # Process files
            task = progress.add_task(
                "Processing files...",
                total=len(files)
            )

            async def process_file(file: Path) -> None:
                try:
                    format_name = formats.get(file)
                    if not format_name:
                        return

                    # Convert file
                    console.print(f"\nConverting {format_name} -> markdown: {file}")
                    doc = converter.convert_file(file, format_name)

                    # Save processed document
                    output_file = output_dir / file.relative_to(input_dir)
                    output_file = output_file.with_suffix(".md")
                    await aiofiles.os.makedirs(str(output_file.parent), exist_ok=True)

                    # Save document asynchronously
                    async with aiofiles.open(str(output_file), 'w') as f:
                        await f.write(doc.content)

                except Exception as e:
                    logger.error(f"Failed to process {file}: {e}")
                    raise click.ClickException(f"Failed to process {file}: {e}")

                progress.advance(task)

            # Process files concurrently
            await asyncio.gather(*[process_file(file) for file in files])

            console.print("\nProcessing complete!")

    def run(self, **kwargs: Any) -> None:
        """Run the command.

        Args:
            **kwargs: Command arguments
        """
        asyncio.run(self.run_async(**kwargs))

    def create_command(self) -> click.Command:
        """Create the process-notes command."""

        @click.command(name=self.name)
        @click.option(
            "--input-dir",
            type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
            help="Directory containing notes to process",
        )
        @click.option(
            "--output-dir",
            type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
            help="Directory to store processed notes",
        )
        def process_notes(input_dir: Optional[Path], output_dir: Optional[Path]) -> None:
            """Process notes with format detection and conversion."""
            self.run(input_dir=input_dir, output_dir=output_dir)

        return process_notes
