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
        # Track processed files to avoid duplicates
        processed_files = set()
        total_copied = 0

        # Create attachments subdirectory in destination
        dest_attachments = dest_dir / "attachments"
        dest_attachments.mkdir(parents=True, exist_ok=True)

        # Check for attachments directory named after the base file in parse output
        attachments_dir = src_dir / base_name
        if attachments_dir.exists() and attachments_dir.is_dir():
            try:
                # Copy all files from the directory
                for file_path in attachments_dir.iterdir():
                    if file_path.is_file() and not file_path.name.startswith('.'):
                        # Skip if already processed
                        if file_path.name in processed_files:
                            continue
                        processed_files.add(file_path.name)

                        # Get the base name without .parsed.md
                        if file_path.name.endswith(".parsed.md"):
                            attachment_base = file_path.stem.replace(".parsed", "")
                            # Copy to destination with .md extension
                            dest_path = dest_attachments / f"{attachment_base}.md"
                            shutil.copy2(file_path, dest_path)
                            # Add to pipeline state for tracking
                            if "attachments" not in self.pipeline.state["disassemble"]:
                                self.pipeline.state["disassemble"]["attachments"] = {}
                            if base_name not in self.pipeline.state["disassemble"]["attachments"]:
                                self.pipeline.state["disassemble"]["attachments"][base_name] = []
                            self.pipeline.state["disassemble"]["attachments"][base_name].append({
                                "path": dest_path,
                                "type": "DOC",
                                "content": file_path.read_text(encoding="utf-8"),
                            })
                        else:
                            # Copy other files (images, etc.) as is
                            dest_path = dest_attachments / file_path.name
                            shutil.copy2(file_path, dest_path)
                            # Add to pipeline state for tracking
                            if "attachments" not in self.pipeline.state["disassemble"]:
                                self.pipeline.state["disassemble"]["attachments"] = {}
                            if base_name not in self.pipeline.state["disassemble"]["attachments"]:
                                self.pipeline.state["disassemble"]["attachments"][base_name] = []
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
                                    if file_type not in ["IMAGE", "PDF", "EXCEL", "DOC", "OTHER"]
                                    else f"Binary file: {file_path.name}"
                                )
                            except UnicodeDecodeError:
                                content = f"Binary file: {file_path.name}"
                            self.pipeline.state["disassemble"]["attachments"][base_name].append({
                                "path": dest_path,
                                "type": file_type,
                                "content": content,
                                "id": file_path.name,
                            })
                        total_copied += 1

                logger.debug(f"Copied {total_copied} attachments from {attachments_dir}")
            except Exception as e:
                self.pipeline.state["disassemble"]["stats"]["attachments"]["failed"] += 1
                logger.error(f"Failed to copy attachments: {str(e)}")

        # Check for .assets directory
        assets_dir = src_dir / f"{base_name}.assets"
        if assets_dir.exists():
            try:
                # Copy all files from assets to attachments
                for asset in assets_dir.iterdir():
                    if asset.is_file() and not asset.name.startswith('.'):
                        # Skip if already processed
                        if asset.name in processed_files:
                            continue
                        processed_files.add(asset.name)

                        dest_path = dest_attachments / asset.name
                        shutil.copy2(asset, dest_path)
                        # Add to pipeline state for tracking
                        if "attachments" not in self.pipeline.state["disassemble"]:
                            self.pipeline.state["disassemble"]["attachments"] = {}
                        if base_name not in self.pipeline.state["disassemble"]["attachments"]:
                            self.pipeline.state["disassemble"]["attachments"][base_name] = []
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
                                if file_type not in ["IMAGE", "PDF", "EXCEL", "DOC", "OTHER"]
                                else f"Binary file: {asset.name}"
                            )
                        except UnicodeDecodeError:
                            content = f"Binary file: {asset.name}"
                        self.pipeline.state["disassemble"]["attachments"][base_name].append({
                            "path": dest_path,
                            "type": file_type,
                            "content": content,
                            "id": asset.name,
                        })
                        total_copied += 1

                logger.debug(f"Copied {total_copied} assets from {assets_dir}")
            except Exception as e:
                self.pipeline.state["disassemble"]["stats"]["attachments"]["failed"] += 1
                logger.error(f"Failed to copy assets: {str(e)}")

        # Check for standalone files in dated directories
        if src_dir.name.startswith("20") and len(src_dir.name) >= 8:
            try:
                # Copy all files from the directory
                for file_path in src_dir.iterdir():
                    if file_path.is_file() and not file_path.name.startswith('.'):
                        # Skip if already processed
                        if file_path.name in processed_files:
                            continue
                        processed_files.add(file_path.name)

                        # Skip markdown files that have a parent markdown file
                        if file_path.suffix.lower() == '.md':
                            parent_md = src_dir.parent / f"{src_dir.name}.md"
                            if parent_md.exists():
                                continue

                        # Copy file to attachments directory
                        dest_path = dest_attachments / file_path.name
                        shutil.copy2(file_path, dest_path)

                        # Add to pipeline state for tracking
                        if "attachments" not in self.pipeline.state["disassemble"]:
                            self.pipeline.state["disassemble"]["attachments"] = {}
                        if base_name not in self.pipeline.state["disassemble"]["attachments"]:
                            self.pipeline.state["disassemble"]["attachments"][base_name] = []

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
                                if file_type not in ["IMAGE", "PDF", "EXCEL", "DOC", "OTHER"]
                                else f"Binary file: {file_path.name}"
                            )
                        except UnicodeDecodeError:
                            content = f"Binary file: {file_path.name}"

                        self.pipeline.state["disassemble"]["attachments"][base_name].append({
                            "path": dest_path,
                            "type": file_type,
                            "content": content,
                            "id": file_path.name,
                        })
                        total_copied += 1

                logger.debug(f"Copied {total_copied} standalone files from {src_dir}")
            except Exception as e:
                self.pipeline.state["disassemble"]["stats"]["attachments"]["failed"] += 1
                logger.error(f"Failed to copy standalone files: {str(e)}")

        # Update stats only once with total copied
        if total_copied > 0:
            self.pipeline.state["disassemble"]["stats"]["attachments"]["copied"] = total_copied

        return total_copied

    def _print_summary(self) -> None:
        """Print phase summary."""
        table = Table(title="Disassembly Phase Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")

        # Get stats
        stats = self.pipeline.state["disassemble"]["stats"]

        # Get the original input files by looking at the base names of processed files
        processed_files = self.pipeline.state["disassemble"].get("successful_files", set())
        unique_files = set()
        for f in processed_files:
            if str(f).endswith(".parsed.md"):
                # Get the original file path by removing .parsed.md
                original_file = str(f).replace(".parsed.md", "")
                # Skip metadata files
                if original_file.endswith(".metadata.json"):
                    continue
                # Skip files that start with . (like .DS_Store)
                if Path(original_file).name.startswith('.'):
                    continue
                # Add the full path to handle duplicates in different directories
                unique_files.add(original_file)

        input_files = len(unique_files)

        table.add_row("Input Files", str(input_files))
        table.add_row(
            "Output Files",
            f"{stats['summary_files']['created']} summaries, {stats['raw_notes_files']['created']} raw notes",
        )
        table.add_row("Total Sections", str(stats.get("total_sections", 0)))
        table.add_row(
            "Summary Files",
            f"{stats['summary_files']['created']} created, {stats['summary_files']['empty']} empty",
        )
        table.add_row(
            "Raw Notes Files",
            f"{stats['raw_notes_files']['created']} created, {stats['raw_notes_files']['empty']} empty",
        )
        table.add_row(
            "Attachments",
            f"{stats['attachments']['copied']} copied, {stats['attachments']['failed']} failed",
        )

        console.print(table)

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
            # Skip non-parsed markdown files and metadata files
            if not str(file_path).endswith(".parsed.md") or ".metadata.json" in str(file_path):
                return metadata

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

            # Create a subdirectory for attachments
            attachments_dir = output_subdir / f"{base_name}.attachments"
            attachments_dir.mkdir(parents=True, exist_ok=True)

            # Load metadata from parse phase if not provided
            if metadata is None:
                metadata_file = file_path.with_suffix(".metadata.json")
                if metadata_file.exists():
                    metadata = FileMetadata.from_json_file(metadata_file)
                else:
                    metadata = FileMetadata.from_file(
                        file_path=file_path,
                        handler_name="disassemble",
                        handler_version="1.0",
                    )

            # Read content
            content = file_path.read_text(encoding="utf-8")

            # Split content into summary and raw notes
            summary_content, raw_notes_content = self._split_content(content)

            # Initialize section count for this file
            section_count = 0
            metadata.metadata["sections"] = {
                "summary": False,
                "raw_notes": False,
                "attachments": [],
                "total_sections": 0,
            }

            logger.debug(
                f"Processing {base_name} - Initial section_count = {section_count}"
            )

            # Write summary file
            if summary_content:
                summary_file = output_subdir / f"{base_name}.summary.md"
                summary_file.write_text(summary_content, encoding="utf-8")
                metadata.add_output_file(summary_file)
                metadata.metadata["sections"]["summary"] = True
                self.pipeline.state["disassemble"]["stats"]["summary_files"][
                    "created"
                ] += 1
                self.pipeline.state["disassemble"]["stats"]["total_outputs"] += 1
                section_count += 1
                logger.debug(
                    f"Created summary file for {base_name}, section_count = {section_count}"
                )
            else:
                self.pipeline.state["disassemble"]["stats"]["summary_files"][
                    "empty"
                ] += 1

            # Write raw notes file if it exists
            if raw_notes_content:
                raw_notes_file = output_subdir / f"{base_name}.rawnotes.md"
                raw_notes_file.write_text(raw_notes_content, encoding="utf-8")
                metadata.add_output_file(raw_notes_file)
                metadata.metadata["sections"]["raw_notes"] = True
                self.pipeline.state["disassemble"]["stats"]["raw_notes_files"][
                    "created"
                ] += 1
                self.pipeline.state["disassemble"]["stats"]["total_outputs"] += 1
                section_count += 1
                logger.debug(
                    f"Created raw notes file for {base_name}, section_count = {section_count}"
                )
            else:
                self.pipeline.state["disassemble"]["stats"]["raw_notes_files"][
                    "empty"
                ] += 1

            # Copy attachments if they exist
            attachment_count = self._copy_attachments(
                file_path.parent, attachments_dir, base_name
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
                
                # Update metadata with attachment info
                if attachments_dir.exists():
                    for file_path in attachments_dir.iterdir():
                        if file_path.is_file() and not file_path.name.startswith('.'):
                            metadata.metadata["sections"]["attachments"].append(
                                str(file_path.relative_to(attachments_dir))
                            )

            # Update total sections in metadata
            metadata.metadata["sections"]["total_sections"] = section_count
            self.pipeline.state["disassemble"]["stats"]["total_sections"] += section_count

            # Save metadata in processing directory, not output directory
            metadata_file = self.pipeline.config.processing_dir / "phases" / "disassemble" / "metadata" / f"{base_name}.metadata.json"
            metadata_file.parent.mkdir(parents=True, exist_ok=True)
            metadata.save(metadata_file)

            # Mark as processed
            metadata.processed = True
            # Track both the original input file path and attachments directory in successful_files
            self.pipeline.state["disassemble"]["successful_files"].add(str(file_path))
            if attachments_dir.exists():
                # Track the output attachments directory
                self.pipeline.state["disassemble"]["successful_files"].add(str(attachments_dir))
                # Track the original attachments directory
                original_attachments_dir = file_path.parent / base_name
                if original_attachments_dir.exists():
                    self.pipeline.state["disassemble"]["successful_files"].add(str(original_attachments_dir))
                # Track the assets directory if it exists
                assets_dir = file_path.parent / f"{base_name}.assets"
                if assets_dir.exists():
                    self.pipeline.state["disassemble"]["successful_files"].add(str(assets_dir))

            # Track the original input file path
            self.pipeline.state["disassemble"]["successful_files"].add(str(file_path))

            return metadata

        except Exception as e:
            error_msg = f"Failed to process file {file_path}: {str(e)}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            if metadata:
                metadata.add_error(self.name, error_msg)
                metadata.processed = False
            self.pipeline.state["disassemble"]["failed_files"].add(str(file_path))
            return metadata

    def finalize(self) -> None:
        """Print summary and cleanup after processing all files."""
        # Ensure we have a newline before printing summary
        console.print()
        self._print_summary()
        console.print()

        # Clear any temporary state
        if "_file_errors" in self.pipeline.state["disassemble"]:
            del self.pipeline.state["disassemble"]["_file_errors"]

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
