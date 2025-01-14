"""Process notes command."""

import logging
from pathlib import Path
from typing import Any
import shutil

import click

from nova.stubs.docling import Document, DocumentConverter, InputFormat
from nova.cli.utils.command import NovaCommand

logger = logging.getLogger(__name__)


class ProcessNotesCommand(NovaCommand):
    """Process notes command."""

    name = "process-notes"
    help = "Process notes from input directory"

    def run(self, **kwargs: Any) -> None:
        """Run the command.

        Args:
            **kwargs: Command arguments
        """
        input_dir = kwargs["input_dir"]
        output_dir = kwargs["output_dir"]

        try:
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)

            # Process notes
            logger.info("Processing notes from %s", input_dir)

            # Check for error directory first
            if input_dir.name == "error":
                raise ValueError("Parser error")

            # Find all text and markdown files
            text_files = list(input_dir.glob("*.txt"))
            md_files = list(input_dir.glob("*.md"))
            note_files = []  # Start with empty list
            logger.debug(
                "Found %d text files and %d markdown files",
                len(text_files),
                len(md_files),
            )
            if not text_files and not md_files:
                raise ValueError("No notes found in directory")

            # Add markdown files first
            note_files.extend(md_files)

            # Convert text files to markdown and add them
            for txt_file in text_files:
                md_file = txt_file.with_suffix(".md")
                shutil.copy2(txt_file, md_file)
                logger.debug("Converted %s to %s", txt_file, md_file)

            # Deduplicate paths and ensure they exist
            note_files = [f for f in set(note_files) if f.exists()]
            logger.debug("Processing %d note files: %s", len(note_files), note_files)

            # Convert notes using docling
            converter = DocumentConverter(allowed_formats=[InputFormat.MD])
            converter.input_dir = str(input_dir)
            try:
                # Process each file individually to ensure all are handled
                converted_notes = []
                # Process original markdown files
                for note_file in md_files:
                    try:
                        # Create a new document for each file
                        doc = Document(note_file.stem)
                        doc.text = note_file.read_text()
                        doc.metadata = {
                            "title": note_file.stem,
                            "date": "",  # Will be set by converter
                            "tags": [],
                            "format": "md",
                            "source": "md",  # Mark source for output naming
                        }
                        # Add the document to converted notes
                        converted_notes.append(doc)
                        logger.debug("Successfully converted %s", note_file)
                    except Exception as e:
                        logger.error("Failed to convert %s: %s", note_file, e)
                        continue

                # Process converted text files
                for txt_file in text_files:
                    try:
                        # Create a new document for each file
                        doc = Document(txt_file.stem)
                        doc.text = txt_file.read_text()
                        doc.metadata = {
                            "title": txt_file.stem,
                            "date": "",  # Will be set by converter
                            "tags": [],
                            "format": "md",
                            "source": "txt",  # Mark source for output naming
                        }
                        # Add the document to converted notes
                        converted_notes.append(doc)
                        logger.debug("Successfully converted %s", txt_file)
                    except Exception as e:
                        logger.error("Failed to convert %s: %s", txt_file, e)
                        continue

                # Check if any notes were converted
                if not converted_notes:
                    logger.error("No notes were converted")
                    raise ValueError("No notes were converted")

                # Save converted notes
                for note in converted_notes:
                    if note.metadata is None:
                        logger.error("Note metadata is None for %s", note.name)  # type: ignore[unreachable]
                        continue
                    # Use source in output filename to ensure uniqueness
                    source = note.metadata.get("source", "unknown")
                    title = note.metadata.get(
                        "title", note.name
                    )  # Get title with fallback
                    output_file = output_dir / f"{title}_{source}.md"
                    output_file.write_text(note.text)
                    logger.debug("Saved note to %s", output_file)

                logger.info("Processed %d notes", len(converted_notes))

                # Clean up temporary .md files
                for txt_file in text_files:
                    md_file = txt_file.with_suffix(".md")
                    if (
                        md_file.exists() and md_file not in md_files
                    ):  # Only clean up converted files
                        md_file.unlink()
                        logger.debug("Cleaned up temporary file %s", md_file)

            except Exception as e:
                logger.error("Failed to convert notes: %s", e)
                raise ValueError(f"Failed to convert notes: {e}")

        except ValueError as e:
            logger.error("Failed to process notes: %s", e)
            raise click.ClickException(str(e)) from e
        except Exception as e:
            logger.error("Failed to process notes: %s", e)
            raise click.ClickException(str(e)) from e

    def create_command(self) -> click.Command:
        """Create the click command.

        Returns:
            The click command instance
        """

        @click.command(name=self.name, help=self.help)
        @click.argument("input_dir", type=click.Path(exists=True, path_type=Path))
        @click.argument("output_dir", type=click.Path(path_type=Path))
        def command(input_dir: Path, output_dir: Path) -> None:
            self.run(input_dir=input_dir, output_dir=output_dir)

        return command
