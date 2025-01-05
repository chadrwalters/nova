"""Split phase implementation."""

# Standard library
import logging
import os
import re
import traceback
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple, Union

# Internal imports
from ..config.manager import ConfigManager
from ..core.markdown import MarkdownWriter
from ..core.metadata import FileMetadata
from ..handlers.base import BaseHandler
from ..handlers.registry import HandlerRegistry
from ..models.document import DocumentMetadata
from .base import Phase

if TYPE_CHECKING:
    from ..core.pipeline import NovaPipeline

logger = logging.getLogger(__name__)


class SplitPhase(Phase):
    """Split phase of the document processing pipeline."""

    # Simple type mapping for organization
    TYPE_MAP = {
        ".docx": "DOC",
        ".doc": "DOC",
        ".pdf": "PDF",
        ".jpg": "IMAGE",
        ".jpeg": "IMAGE",
        ".heic": "IMAGE",
        ".png": "IMAGE",
        ".svg": "IMAGE",
        ".html": "DOC",
        ".txt": "TXT",
        ".json": "JSON",
        ".xlsx": "EXCEL",
        ".xls": "EXCEL",
        ".csv": "EXCEL",
        ".md": "DOC",
    }

    def __init__(
        self, config: ConfigManager, pipeline: Optional["NovaPipeline"] = None
    ):
        """Initialize split phase.

        Args:
            config: Configuration manager
            pipeline: Optional pipeline instance
        """
        super().__init__("split", config, pipeline)
        self.handler_registry = HandlerRegistry(config)

        # Initialize state
        self.section_stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"total": 0, "successful": 0, "failed": 0}
        )

        self.stats: defaultdict[str, Dict[str, int]] = defaultdict(
            lambda: {"processed": 0, "skipped": 0, "errors": 0}
        )

        # Initialize attachments storage
        self._all_attachments: Dict[str, List[Dict[str, str]]] = {}

    def _get_file_type(self, path: str) -> str:
        """Get standardized file type from path."""
        ext = Path(path).suffix.lower()
        return self.TYPE_MAP.get(ext, "OTHER")

    def _make_reference(self, path: str, is_note: bool = False) -> str:
        """Create a reference marker for a path.

        Args:
            path: Path to create reference for
            is_note: Whether this is a note reference

        Returns:
            Reference marker string
        """
        # Extract name without any extensions
        name = Path(path).stem
        # Remove .parsed extension if present
        if name.endswith(".parsed"):
            name = name[:-7]

        # If it's a note, use [NOTE:name] format
        if is_note:
            return f"[NOTE:{name}]"

        # For attachments, use [ATTACH:TYPE:name] format
        file_type = self._get_file_type(path)
        return f"[ATTACH:{file_type}:{name}]"

    def _extract_attachments(self, file_path: Path) -> List[Dict]:
        """Extract attachments from a file."""
        attachments = []
        seen_refs = set()

        # Function to process attachments from a directory
        def process_directory(dir_path: Path, relative_path: str = "") -> List[Dict]:
            result = []
            if dir_path.exists() and dir_path.is_dir():
                # Process all files in this directory
                for attachment_path in dir_path.glob("*.*"):
                    if attachment_path.is_file():
                        # Get file type from extension
                        file_type = self._get_file_type(str(attachment_path))

                        # Create reference using just the base name
                        base_name = attachment_path.stem
                        if base_name.endswith(".parsed"):
                            # Remove .parsed extension
                            base_name = base_name[:-7]  # Remove '.parsed'
                        else:
                            # For non-parsed files, just use the stem
                            base_name = base_name

                        # Create reference marker
                        ref = self._make_reference(str(attachment_path))

                        # Skip if we've seen this reference before
                        if ref in seen_refs:
                            continue
                        seen_refs.add(ref)

                        # Add attachment info
                        result.append(
                            {
                                "path": str(attachment_path),
                                "type": file_type,
                                "name": base_name,
                                "directory": relative_path,
                                "ref": ref,
                            }
                        )

            return result

        # Process attachments from the file's directory
        attachments.extend(process_directory(file_path.parent))

        # Process attachments from subdirectories
        for subdir in file_path.parent.glob("**/"):
            if subdir != file_path.parent:
                rel_path = str(subdir.relative_to(file_path.parent))
                attachments.extend(process_directory(subdir, rel_path))

        return attachments

    def _build_attachments_markdown(self, attachments: List[Dict]) -> str:
        """Build markdown content for attachments file."""
        content = ["# Attachments\n"]

        # Group attachments by directory first, then by type
        by_directory: defaultdict[str, defaultdict[str, list[Dict]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for attachment in attachments:
            directory = attachment.get("directory", "")
            file_type = attachment["type"]
            by_directory[directory][file_type].append(attachment)

        # Build sections for each directory
        for directory in sorted(by_directory.keys()):
            if directory:
                content.append(f"\n## Directory: {directory}\n")

            # Build sections for each type within the directory
            for file_type in sorted(by_directory[directory].keys()):
                content.append(f"\n### {file_type} Files\n")
                for attachment in sorted(
                    by_directory[directory][file_type], key=lambda x: x["name"]
                ):
                    content.append(f"- {attachment['ref']}")

        return "\n".join(content)

    async def process_impl(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: Optional[DocumentMetadata] = None,
    ) -> Optional[DocumentMetadata]:
        """Process a file by splitting it into sections.

        Args:
            file_path: Path to file to process
            output_dir: Output directory
            metadata: Optional metadata from previous phase

        Returns:
            Updated metadata or None if processing failed
        """
        try:
            # Create metadata if not provided
            if metadata is None:
                metadata = DocumentMetadata.from_file(
                    file_path=file_path,
                    handler_name="split",
                    handler_version="1.0",
                )

            # Track sections for each output file
            summary_sections = []
            raw_notes_sections = []
            attachments: Dict[str, List[Dict]] = {}

            # Get base name without extensions
            base_name = file_path.stem
            if base_name.endswith(".summary"):
                base_name = base_name[:-8]  # Remove '.summary'
            elif base_name.endswith(".rawnotes"):
                base_name = base_name[:-9]  # Remove '.rawnotes'

            # Look for related files in the same directory
            summary_file = file_path.parent / f"{base_name}.summary.md"
            raw_notes_file = file_path.parent / f"{base_name}.rawnotes.md"

            # Process summary file if it exists
            if summary_file.exists():
                summary_content = summary_file.read_text(encoding="utf-8")
                if summary_content.strip():
                    summary_sections.append(summary_content)

            # Process raw notes file if it exists
            if raw_notes_file.exists():
                raw_notes_content = raw_notes_file.read_text(encoding="utf-8")
                if raw_notes_content.strip():
                    raw_notes_sections.append(raw_notes_content)

            # Get parent directory name for attachments
            parent_dir = file_path.parent.name
            if parent_dir not in attachments:
                attachments[parent_dir] = []

            # Get attachments from parse phase
            parse_dir = self.pipeline.config.processing_dir / "phases" / "parse"
            if parse_dir.exists():
                # Look for files in the same directory as the input file
                input_dir = file_path.parent
                for file_path in input_dir.glob("*.*"):
                    if file_path.is_file() and not file_path.name.endswith(
                        (".summary.md", ".rawnotes.md")
                    ):
                        # Get file type from extension
                        file_ext = file_path.suffix.lower()
                        file_type = self.TYPE_MAP.get(file_ext, "OTHER")

                        # Create reference marker
                        ref = self._make_reference(str(file_path))

                        attachment = {
                            "path": str(file_path),
                            "id": file_path.stem,
                            "type": file_type,
                            "name": file_path.stem,
                            "ref": ref,
                            "content": (
                                f"Binary file: {file_path.name}"
                                if file_type
                                in ["IMAGE", "PDF", "EXCEL", "DOC", "OTHER"]
                                or file_path.name.startswith(
                                    "."
                                )  # Skip hidden files like .DS_Store
                                else file_path.read_text(encoding="utf-8")
                            ),
                        }
                        attachments[parent_dir].append(attachment)

            # Write or append to consolidated files
            if summary_sections:
                summary_file = output_dir / "Summary.md"
                # Read existing content if file exists
                existing_content = (
                    summary_file.read_text(encoding="utf-8")
                    if summary_file.exists()
                    else ""
                )
                # Append new content with a separator
                full_content = (
                    existing_content
                    + ("\n\n" if existing_content else "")
                    + "\n\n".join(summary_sections)
                )
                summary_file.write_text(full_content, encoding="utf-8")
                metadata.add_output_file(summary_file)

            if raw_notes_sections:
                raw_notes_file = output_dir / "Raw Notes.md"
                # Read existing content if file exists
                existing_content = (
                    raw_notes_file.read_text(encoding="utf-8")
                    if raw_notes_file.exists()
                    else ""
                )
                # Append new content with a separator
                full_content = (
                    existing_content
                    + ("\n\n" if existing_content else "")
                    + "\n\n".join(raw_notes_sections)
                )
                raw_notes_file.write_text(full_content, encoding="utf-8")
                metadata.add_output_file(raw_notes_file)

            if attachments:
                # Store attachments for finalize phase
                if not hasattr(self, "_all_attachments"):
                    self._all_attachments = {}
                self._all_attachments.update(attachments)

                # Write attachments file
                attachments_file = output_dir / "Attachments.md"
                self._write_attachments_file(attachments, output_dir)
                if attachments_file.exists():
                    metadata.add_output_file(attachments_file)

            metadata.processed = True
            return metadata

        except Exception as e:
            self.logger.error(f"Failed to split file: {file_path}")
            self.logger.error(traceback.format_exc())
            if metadata:
                metadata.add_error("SplitPhase", str(e))
            return metadata

    def _update_section_stats(self, section: str, status: str) -> None:
        """Update section processing statistics."""
        if section in self.section_stats and status in self.section_stats[section]:
            self.section_stats[section][status] += 1

    def finalize(self) -> None:
        """Finalize phase processing."""
        try:
            # Get output directory
            output_dir = self.pipeline.get_phase_output_dir("split")

            # Write consolidated attachments file
            if self._all_attachments:
                attachments_file = self._write_attachments_file(
                    self._all_attachments, output_dir
                )
                self.logger.info(f"Wrote attachments to {attachments_file}")

            # Log stats
            self.logger.info("Split phase stats:")
            for file_type, stats in self.stats.items():
                self.logger.info(
                    f"{file_type}: {stats['processed']} processed, "
                    f"{stats['skipped']} skipped, {stats['errors']} errors"
                )

            self.logger.info("Section stats:")
            for section, stats in self.section_stats.items():
                self.logger.info(
                    f"{section}: {stats['processed']} processed, "
                    f"{stats['empty']} empty, {stats['error']} errors"
                )

        except Exception as e:
            self.logger.error(f"Error in finalize: {str(e)}")
            self.logger.debug(traceback.format_exc())

    def _write_attachments_file(
        self, attachments: Dict[str, List[Dict[str, str]]], output_dir: Path
    ) -> Path:
        """Write attachments to a consolidated file.

        Args:
            attachments: Dictionary of attachments by directory
            output_dir: Output directory

        Returns:
            Path to the written attachments file
        """
        # Create attachments file
        attachments_file = output_dir / "Attachments.md"
        attachments_file.parent.mkdir(parents=True, exist_ok=True)

        # Build markdown content
        content = ["# Attachments\n"]

        # Add sections for each directory
        for directory, dir_attachments in sorted(attachments.items()):
            if directory:
                content.append(f"\n## Directory: {directory}\n")

            # Group attachments by type
            by_type: defaultdict[str, list[Dict[str, str]]] = defaultdict(list)
            for attachment in dir_attachments:
                file_type = attachment["type"]
                by_type[file_type].append(attachment)

            # Add sections for each type
            for file_type, type_attachments in sorted(by_type.items()):
                content.append(f"\n### {file_type} Files\n")
                for attachment in sorted(type_attachments, key=lambda x: x["name"]):
                    content.append(f"- {attachment['ref']}")

        # Write content to file
        attachments_file.write_text("\n".join(content), encoding="utf-8")
        return attachments_file
