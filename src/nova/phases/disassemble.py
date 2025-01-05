"""Disassembly phase of the Nova pipeline."""

# Standard library
import logging
import os
import shutil
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple, Union

# External dependencies
from rich.console import Console
from rich.table import Table

# Internal imports
from ..config.manager import ConfigManager
from ..core.metadata import FileMetadata
from ..handlers.registry import HandlerRegistry
from ..phases.base import Phase

if TYPE_CHECKING:
    from ..core.pipeline import NovaPipeline

logger = logging.getLogger(__name__)
console = Console()


class DisassemblyPhase(Phase):
    """Phase that splits parsed markdown files into summary and raw notes components."""

    def __init__(
        self, config: ConfigManager, pipeline: Optional["NovaPipeline"] = None
    ):
        """Initialize the disassembly phase."""
        super().__init__("disassemble", config, pipeline)
        self.handler_registry = HandlerRegistry(config)

        # Initialize state
        if "disassemble" not in self.pipeline.state:
            self.pipeline.state["disassemble"] = {}

        # Update state with required keys
        state = self.pipeline.state["disassemble"]

        # Always reset stats at the start of a new run
        state["stats"] = {
            "summary_files": {"created": 0, "empty": 0, "failed": 0},
            "raw_notes_files": {"created": 0, "empty": 0, "failed": 0},
            "attachments": {"copied": 0, "failed": 0},
            "total_sections": 0,
            "total_processed": 0,
            "total_attachments": 0,
            "total_outputs": 0,
        }

        if "successful_files" not in state:
            state["successful_files"] = set()
        if "failed_files" not in state:
            state["failed_files"] = set()
        if "skipped_files" not in state:
            state["skipped_files"] = set()
        if "unchanged_files" not in state:
            state["unchanged_files"] = set()
        if "reprocessed_files" not in state:
            state["reprocessed_files"] = set()
        if "attachments" not in state:
            state["attachments"] = {}
        if "_file_errors" not in state:
            state["_file_errors"] = {}

    def _copy_attachments(self, src_dir: Path, dest_dir: Path, base_name: str) -> int:
        """Copy attachments directory if it exists.

        Args:
            src_dir: Source directory containing attachments
            dest_dir: Destination directory for attachments
            base_name: Base name of the file being processed (without .parsed)

        Returns:
            Number of attachments copied
        """
        attachment_count = 0

        # Check for attachments directory named after the base file in parse output
        attachments_dir = src_dir / base_name
        if attachments_dir.exists() and attachments_dir.is_dir():
            try:
                # Create base name directory in destination
                dest_attachments = dest_dir / base_name
                if dest_attachments.exists():
                    shutil.rmtree(dest_attachments)

                # Create the destination directory
                dest_attachments.mkdir(parents=True, exist_ok=True)

                # Copy all files from the directory
                for file_path in attachments_dir.iterdir():
                    if file_path.is_file():
                        attachment_count += 1
                        # Get the base name without .parsed.md
                        if file_path.name.endswith(".parsed.md"):
                            attachment_base = file_path.stem.replace(".parsed", "")
                            # Copy to destination with .md extension
                            dest_path = dest_attachments / f"{attachment_base}.md"
                            shutil.copy2(file_path, dest_path)
                            # Add to pipeline state for tracking
                            if "attachments" not in self.pipeline.state["disassemble"]:
                                self.pipeline.state["disassemble"]["attachments"] = {}
                            if (
                                base_name
                                not in self.pipeline.state["disassemble"]["attachments"]
                            ):
                                self.pipeline.state["disassemble"]["attachments"][
                                    base_name
                                ] = []
                            self.pipeline.state["disassemble"]["attachments"][
                                base_name
                            ].append(
                                {
                                    "path": dest_path,
                                    "type": "DOC",
                                    "content": file_path.read_text(encoding="utf-8"),
                                }
                            )
                        else:
                            # Copy other files (images, etc.) as is
                            dest_path = dest_attachments / file_path.name
                            shutil.copy2(file_path, dest_path)
                            # Add to pipeline state for tracking
                            if "attachments" not in self.pipeline.state["disassemble"]:
                                self.pipeline.state["disassemble"]["attachments"] = {}
                            if (
                                base_name
                                not in self.pipeline.state["disassemble"]["attachments"]
                            ):
                                self.pipeline.state["disassemble"]["attachments"][
                                    base_name
                                ] = []
                            # Get file type from extension
                            file_ext = file_path.suffix.lower()
                            file_type = {
                                ".pdf": "PDF",
                                ".doc": "DOC",
                                ".docx": "DOC",
                                ".xls": "EXCEL",
                                ".xlsx": "EXCEL",
                                ".csv": "EXCEL",
                                ".txt": "TXT",
                                ".json": "JSON",
                                ".png": "IMAGE",
                                ".jpg": "IMAGE",
                                ".jpeg": "IMAGE",
                                ".heic": "IMAGE",
                                ".svg": "IMAGE",
                                ".gif": "IMAGE",
                            }.get(file_ext, "OTHER")
                            try:
                                content = (
                                    file_path.read_text(encoding="utf-8")
                                    if file_type not in ["IMAGE", "PDF", "EXCEL"]
                                    else f"Binary file: {file_path.name}"
                                )
                            except UnicodeDecodeError:
                                content = f"Binary file: {file_path.name}"
                            # Use just the file name as the key
                            attachment_key = file_path.name
                            if attachment_key.endswith(".parsed"):
                                attachment_key = attachment_key[:-7]
                            self.pipeline.state["disassemble"]["attachments"][
                                base_name
                            ].append(
                                {
                                    "path": dest_path,
                                    "type": file_type,
                                    "content": content,
                                    "id": attachment_key,
                                }
                            )

                self.pipeline.state["disassemble"]["stats"]["attachments"][
                    "copied"
                ] += attachment_count
                logger.debug(
                    f"Copied {attachment_count} attachments from {attachments_dir}"
                )
            except Exception as e:
                self.pipeline.state["disassemble"]["stats"]["attachments"][
                    "failed"
                ] += 1
                logger.error(f"Failed to copy attachments: {str(e)}")

        # Check for .assets directory
        assets_dir = src_dir / f"{base_name}.assets"
        if assets_dir.exists():
            try:
                # Create attachments directory if it doesn't exist
                dest_attachments = dest_dir / base_name
                dest_attachments.mkdir(parents=True, exist_ok=True)

                # Copy all files from assets to attachments
                for asset in assets_dir.iterdir():
                    if asset.is_file():
                        attachment_count += 1
                        dest_path = dest_attachments / asset.name
                        shutil.copy2(asset, dest_path)
                        # Add to pipeline state for tracking
                        if "attachments" not in self.pipeline.state["disassemble"]:
                            self.pipeline.state["disassemble"]["attachments"] = {}
                        if (
                            base_name
                            not in self.pipeline.state["disassemble"]["attachments"]
                        ):
                            self.pipeline.state["disassemble"]["attachments"][
                                base_name
                            ] = []
                        # Get file type from extension
                        file_ext = asset.suffix.lower()
                        file_type = {
                            ".pdf": "PDF",
                            ".doc": "DOC",
                            ".docx": "DOC",
                            ".xls": "EXCEL",
                            ".xlsx": "EXCEL",
                            ".csv": "EXCEL",
                            ".txt": "TXT",
                            ".json": "JSON",
                            ".png": "IMAGE",
                            ".jpg": "IMAGE",
                            ".jpeg": "IMAGE",
                            ".heic": "IMAGE",
                            ".svg": "IMAGE",
                            ".gif": "IMAGE",
                        }.get(file_ext, "OTHER")
                        try:
                            content = (
                                asset.read_text(encoding="utf-8")
                                if file_type not in ["IMAGE", "PDF", "EXCEL"]
                                else f"Binary file: {asset.name}"
                            )
                        except UnicodeDecodeError:
                            content = f"Binary file: {asset.name}"
                        # Use just the file name as the key
                        attachment_key = asset.name
                        if attachment_key.endswith(".parsed"):
                            attachment_key = attachment_key[:-7]
                        self.pipeline.state["disassemble"]["attachments"][
                            base_name
                        ].append(
                            {
                                "path": dest_path,
                                "type": file_type,
                                "content": content,
                                "id": attachment_key,
                            }
                        )

                self.pipeline.state["disassemble"]["stats"]["attachments"][
                    "copied"
                ] += attachment_count
                logger.info(f"Copied {attachment_count} assets from {assets_dir}")
            except Exception as e:
                self.pipeline.state["disassemble"]["stats"]["attachments"][
                    "failed"
                ] += 1
                logger.error(f"Failed to copy assets: {str(e)}")

        return attachment_count

    def _print_summary(self):
        """Print processing summary table."""
        stats = self.pipeline.state["disassemble"]["stats"]

        table = Table(title="Disassemble Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", justify="right")

        # Add total sections row
        total_sections = stats.get("total_sections", 0)
        table.add_row("Total Sections", str(total_sections))

        # Add total attachments row
        total_attachments = stats.get("total_attachments", 0)
        table.add_row("Total Attachments", str(total_attachments))

        # Always show the table if we processed any files
        if stats["total_processed"] > 0:
            logger.info("\n" + str(table))

        # Log failed files with their errors
        failed_files = self.pipeline.state["disassemble"]["failed_files"]
        if failed_files:
            logger.error(f"\nFailed to process {len(failed_files)} files:")
            for file_path in failed_files:
                # Get error message if available in metadata
                error_msg = ""
                if file_path in self.pipeline.state["disassemble"]["_file_errors"]:
                    error_msg = f": {self.pipeline.state['disassemble']['_file_errors'][file_path]}"
                logger.error(f"  - {file_path}{error_msg}")
            # Indicate phase failure
            logger.error("\nDisassembly phase completed with errors")
            self.pipeline.state["disassemble"]["phase_failed"] = True
        else:
            logger.info("All files processed successfully")
            self.pipeline.state["disassemble"]["phase_failed"] = False

    def _split_content(self, content: str) -> Tuple[str, Optional[str]]:
        """Split content into summary and raw notes if marker exists.

        Args:
            content: The full file content to split

        Returns:
            Tuple of (summary_content, raw_notes_content)
            raw_notes_content will be None if no split marker found
        """
        SPLIT_MARKER = "--==RAW NOTES==--"

        if SPLIT_MARKER not in content:
            return content.strip(), None

        parts = content.split(SPLIT_MARKER, maxsplit=1)
        summary = parts[0].strip()
        raw_notes = parts[1].strip() if len(parts) > 1 else ""

        return summary, raw_notes

    async def process_impl(
        self, file_path: Path, output_dir: Path, metadata: Optional[FileMetadata] = None
    ) -> Optional[FileMetadata]:
        """Process a file through the disassembly phase.

        Args:
            file_path: Path to file to process
            output_dir: Output directory
            metadata: Optional metadata from previous phase

        Returns:
            Updated metadata if successful, None if failed
        """
        try:
            # Skip non-parsed markdown files
            if not str(file_path).endswith(".parsed.md"):
                return metadata

            # Initialize metadata if not provided
            if metadata is None:
                metadata = FileMetadata.from_file(
                    file_path=file_path,
                    handler_name="disassemble",
                    handler_version="1.0",
                )

            # Read content
            content = file_path.read_text(encoding="utf-8")

            # Split content into summary and raw notes
            summary_content, raw_notes_content = self._split_content(content)

            # Get base name without .parsed.md extension
            base_name = file_path.stem.replace(".parsed", "")

            # Get relative path from parse directory to maintain structure
            parse_dir = self.pipeline.config.processing_dir / "phases" / "parse"
            try:
                rel_path = file_path.relative_to(parse_dir)
                # Use parent directory structure but exclude the filename
                output_subdir = output_dir / rel_path.parent
            except ValueError:
                # If not under parse_dir, use the parent directory name
                output_subdir = output_dir / file_path.parent.name

            # Create output directory
            output_subdir.mkdir(parents=True, exist_ok=True)

            # Initialize section count for this file
            section_count = 0

            logger.debug(
                f"Processing {base_name} - Initial section_count = {section_count}"
            )
            logger.debug(
                f"Current total sections: {self.pipeline.state['disassemble']['stats'].get('total_sections', 0)}"
            )

            # Write summary file
            if summary_content:
                summary_file = output_subdir / f"{base_name}.summary.md"
                summary_file.write_text(summary_content, encoding="utf-8")
                metadata.add_output_file(summary_file)
                self.pipeline.state["disassemble"]["stats"]["summary_files"][
                    "created"
                ] += 1
                self.pipeline.state["disassemble"]["stats"]["total_outputs"] += 1
                section_count += 1
                logger.debug(
                    f"Created summary file for {base_name}, section_count = {section_count}"
                )
                logger.debug(f"Summary content length: {len(summary_content)}")
            else:
                self.pipeline.state["disassemble"]["stats"]["summary_files"][
                    "empty"
                ] += 1
                logger.debug(f"No summary content for {base_name}")

            # Write raw notes file if it exists
            if raw_notes_content:
                raw_notes_file = output_subdir / f"{base_name}.rawnotes.md"
                raw_notes_file.write_text(raw_notes_content, encoding="utf-8")
                metadata.add_output_file(raw_notes_file)
                self.pipeline.state["disassemble"]["stats"]["raw_notes_files"][
                    "created"
                ] += 1
                self.pipeline.state["disassemble"]["stats"]["total_outputs"] += 1
                section_count += 1
                logger.debug(
                    f"Created raw notes file for {base_name}, section_count = {section_count}"
                )
                logger.debug(f"Raw notes content length: {len(raw_notes_content)}")
            else:
                self.pipeline.state["disassemble"]["stats"]["raw_notes_files"][
                    "empty"
                ] += 1
                logger.debug(f"No raw notes content for {base_name}")

            # Copy attachments if they exist
            attachment_count = self._copy_attachments(
                file_path.parent, output_subdir, base_name
            )
            if attachment_count > 0:
                # Initialize total_attachments if not present
                if (
                    "total_attachments"
                    not in self.pipeline.state["disassemble"]["stats"]
                ):
                    self.pipeline.state["disassemble"]["stats"]["total_attachments"] = 0
                self.pipeline.state["disassemble"]["stats"][
                    "total_attachments"
                ] += attachment_count
                logger.debug(f"Added {attachment_count} attachments for {base_name}")

            # Update total sections count
            if "total_sections" not in self.pipeline.state["disassemble"]["stats"]:
                self.pipeline.state["disassemble"]["stats"]["total_sections"] = 0
            current_total = self.pipeline.state["disassemble"]["stats"][
                "total_sections"
            ]
            self.pipeline.state["disassemble"]["stats"][
                "total_sections"
            ] += section_count
            new_total = self.pipeline.state["disassemble"]["stats"]["total_sections"]
            logger.debug(
                f"Updated total sections for {base_name}: {current_total} + {section_count} = {new_total}"
            )

            # Update pipeline state
            self.pipeline.state["disassemble"]["successful_files"].add(file_path)
            self.pipeline.state["disassemble"]["stats"]["total_processed"] += 1

            metadata.processed = True
            return metadata

        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.logger.error(f"Failed to process file {file_path}: {error_msg}")
            self.pipeline.state["disassemble"]["failed_files"].add(file_path)
            self.pipeline.state["disassemble"]["_file_errors"][file_path] = error_msg
            if metadata:
                metadata.add_error("DisassemblyPhase", error_msg)
            # Update failed stats
            self.pipeline.state["disassemble"]["stats"]["summary_files"]["failed"] += 1
            self.pipeline.state["disassemble"]["stats"]["raw_notes_files"][
                "failed"
            ] += 1
            return metadata

    def finalize(self):
        """Finalize the disassembly phase."""
        self._print_summary()
        logger.debug("Disassembly phase complete")
        # Return failure status
        return not self.pipeline.state["disassemble"].get("phase_failed", False)

    async def process_file(
        self, file_path: Union[str, Path], output_dir: Union[str, Path]
    ) -> Optional[FileMetadata]:
        """Process a file through the disassembly phase.

        Args:
            file_path: Path to file to process
            output_dir: Output directory

        Returns:
            Updated metadata if successful, None if failed
        """
        try:
            # Convert to Path objects
            file_path = Path(file_path)
            output_dir = Path(output_dir)
            return await self.process_impl(file_path, output_dir)
        except Exception as e:
            self.logger.error(f"Failed to process file {file_path}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            self.pipeline.state["disassemble"]["failed_files"].add(file_path)
            return None
