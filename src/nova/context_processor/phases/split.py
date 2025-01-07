"""Split phase implementation."""

# Standard library
import logging
import os
import re
import traceback
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple, Union
import json

# Internal imports
from ..config.manager import ConfigManager
from ..core.markdown import MarkdownWriter
from ..core.metadata import DocumentMetadata, FileMetadata
from ..handlers.base import BaseHandler
from ..handlers.registry import HandlerRegistry
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
        """Initialize split phase."""
        super().__init__("split", config, pipeline)
        self.handler_registry = HandlerRegistry(config)

        # Initialize state
        self.section_stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"total": 0, "successful": 0, "failed": 0}
        )

        self.stats: defaultdict[str, Dict[str, int]] = defaultdict(
            lambda: {"processed": 0, "skipped": 0, "errors": 0}
        )

        # Initialize storage for sections and attachments
        self._summary_sections: List[str] = []
        self._raw_notes_sections: List[str] = []
        self._all_attachments: Dict[str, List[Dict[str, str]]] = {}
        self._seen_attachment_paths: Set[str] = set()  # Track all seen attachment paths

    def _get_file_type(self, path: str) -> str:
        """Get standardized file type from path."""
        ext = Path(path).suffix.lower()
        return self.TYPE_MAP.get(ext, "OTHER")

    def _make_reference(self, file_path: str, relative_dir: str = "", override_type: str = None) -> str:
        """Create a reference marker for an attachment.

        Args:
            file_path: Path to the attachment file
            relative_dir: Relative directory path from input root
            override_type: Optional type to use instead of inferring from extension

        Returns:
            Reference marker in the format [ATTACH:TYPE:NAME]
        """
        # Get file type from extension or use override
        file_type = override_type if override_type else self.TYPE_MAP.get(Path(file_path).suffix.lower(), "OTHER")

        # Get base name without extension
        base_name = Path(file_path).stem
        if base_name.endswith(".parsed"):
            base_name = base_name[:-7]  # Remove '.parsed'

        # Create reference marker
        return f"[ATTACH:{file_type}:{base_name}]"

    def _extract_attachments(self, file_path: Path) -> List[Dict]:
        """Extract attachments from a file."""
        attachments = []

        # Function to process attachments from a directory
        def process_directory(dir_path: Path, relative_path: str = "") -> List[Dict]:
            result = []
            if dir_path.exists() and dir_path.is_dir():
                # Process all files in this directory
                for attachment_path in dir_path.glob("*.*"):
                    if attachment_path.is_file():
                        # Get absolute path for deduplication
                        abs_path = str(attachment_path.resolve())
                        
                        # Skip if we've seen this path before
                        if abs_path in self._seen_attachment_paths:
                            continue
                        self._seen_attachment_paths.add(abs_path)

                        # Get file type from extension
                        file_type = self._get_file_type(str(attachment_path))

                        # Create reference using directory and base name
                        base_name = attachment_path.stem
                        if base_name.endswith(".parsed"):
                            base_name = base_name[:-7]  # Remove '.parsed'

                        # Create reference marker with directory context
                        ref = self._make_reference(str(attachment_path), relative_path)

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
        """Process a file by collecting its sections.

        Args:
            file_path: Path to file to process
            output_dir: Output directory
            metadata: Optional metadata from previous phase

        Returns:
            Updated metadata or None if processing failed
        """
        try:
            # Skip raw notes files - we'll get them when processing their paired summary file
            if file_path.stem.endswith(".rawnotes"):
                if metadata is None:
                    metadata = DocumentMetadata.from_file(
                        file_path=file_path,
                        handler_name="split",
                        handler_version="1.0",
                    )
                metadata.processed = True
                return metadata

            # Create metadata if not provided
            if metadata is None:
                metadata = DocumentMetadata.from_file(
                    file_path=file_path,
                    handler_name="split",
                    handler_version="1.0",
                )

            # Get base name without extensions
            base_name = file_path.stem
            if base_name.endswith(".summary"):
                base_name = base_name[:-8]  # Remove '.summary'
            elif base_name.endswith(".parsed"):
                base_name = base_name[:-7]  # Remove '.parsed'

            # Look for related files in the disassemble phase directory
            disassemble_dir = self.pipeline.config.processing_dir / "phases" / "disassemble"
            summary_file = file_path if file_path.name.endswith((".summary.md", ".parsed.md")) else disassemble_dir / f"{base_name}.summary.md"
            raw_notes_file = disassemble_dir / f"{base_name}.rawnotes.md"

            # Create note ID from base name
            note_id = base_name

            # Collect summary content if it exists
            if summary_file.exists():
                summary_content = summary_file.read_text(encoding="utf-8")
                if summary_content.strip():
                    # Add note reference at the end of the summary
                    summary_with_ref = f"{summary_content.strip()}\n\nSee raw notes: [NOTE:{note_id}]"
                    self._summary_sections.append(summary_with_ref)

            # Collect raw notes content if it exists
            if raw_notes_file.exists():
                raw_notes_content = raw_notes_file.read_text(encoding="utf-8")
                if raw_notes_content.strip():
                    # Add note ID at the start of the raw notes
                    raw_notes_with_id = f"[NOTE:{note_id}]\n\n{raw_notes_content.strip()}"
                    self._raw_notes_sections.append(raw_notes_with_id)

            # Get attachments from the pipeline state
            if self.pipeline and "disassemble" in self.pipeline.state:
                disassemble_state = self.pipeline.state["disassemble"]
                if "attachments" in disassemble_state:
                    attachments = disassemble_state["attachments"]
                    if isinstance(attachments, dict):
                        # Get the directory name from the base name
                        parent_dir = str(Path(base_name).parent)
                        
                        # Initialize attachments for this directory if needed
                        if parent_dir not in self._all_attachments:
                            self._all_attachments[parent_dir] = []
                        
                        # Process each attachment in the state
                        for base_key, base_attachments in attachments.items():
                            # Skip if this base key doesn't match our base name
                            if not base_key.startswith(base_name):
                                continue
                            
                            for attachment in base_attachments:
                                # Skip if we've seen this path before
                                abs_path = str(Path(attachment["path"]).resolve())
                                if abs_path in self._seen_attachment_paths:
                                    continue
                                
                                # Add to seen paths
                                self._seen_attachment_paths.add(abs_path)
                                
                                # Get file type from metadata if available
                                file_type = attachment.get("type")
                                if not file_type:
                                    file_type = self._get_file_type(str(attachment["path"]))
                                
                                # Create attachment info
                                new_attachment_info = {
                                    "path": str(attachment["path"]),
                                    "type": file_type,
                                    "name": Path(attachment["path"]).stem,
                                    "directory": parent_dir,
                                    "ref": self._make_reference(str(attachment["path"]), parent_dir, file_type),
                                }
                                
                                # Only add content for markdown files
                                if Path(attachment["path"]).suffix.lower() == '.md':
                                    try:
                                        new_attachment_info["content"] = Path(attachment["path"]).read_text(encoding="utf-8")
                                    except Exception:
                                        logger.warning(f"Failed to read content from {attachment['path']}")
                                
                                # Add to attachments list
                                self._all_attachments[parent_dir].append(new_attachment_info)

            # Mark as processed and return metadata
            metadata.processed = True
            return metadata

        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            return None

    def _update_section_stats(self, section: str, status: str) -> None:
        """Update section processing statistics."""
        if section in self.section_stats and status in self.section_stats[section]:
            self.section_stats[section][status] += 1

    def finalize(self) -> None:
        """Write all collected sections to their respective files."""
        try:
            # Get output directory
            output_dir = self.pipeline.get_phase_output_dir("split")

            # Write summary sections
            if self._summary_sections:
                summary_file = output_dir / "Summary.md"
                summary_file.write_text("\n\n".join(self._summary_sections), encoding="utf-8")

            # Write raw notes sections
            if self._raw_notes_sections:
                raw_notes_file = output_dir / "Raw Notes.md"
                raw_notes_file.write_text("\n\n".join(self._raw_notes_sections), encoding="utf-8")

            # Write attachments
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
        """Write attachments to a consolidated file."""
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
                    # Add the reference and file info
                    content.append(f"\n#### {attachment['name']}\n")
                    content.append(f"- Reference: {attachment['ref']}")
                    
                    # Add content only for markdown files
                    if "content" in attachment and attachment["type"] == "DOC":
                        # Clean up the content
                        clean_content = attachment["content"].strip()
                        
                        # Fix table formatting by removing line breaks in table rows
                        if "|" in clean_content:
                            lines = []
                            in_table = False
                            current_row = []
                            
                            for line in clean_content.splitlines():
                                line = line.rstrip()
                                if line.startswith("|"):
                                    in_table = True
                                    current_row.append(line)
                                elif in_table and line.strip():
                                    current_row.append(line)
                                else:
                                    if current_row:
                                        # Join and clean up the row
                                        row = " ".join(current_row)
                                        # Fix column alignment
                                        row = row.replace("| ", "|").replace(" |", "|")
                                        lines.append(row)
                                        current_row = []
                                    in_table = False
                                    lines.append(line)
                            
                            if current_row:
                                # Join and clean up the last row
                                row = " ".join(current_row)
                                # Fix column alignment
                                row = row.replace("| ", "|").replace(" |", "|")
                                lines.append(row)
                            
                            clean_content = "\n".join(lines)
                        
                        # Remove duplicate content in env files
                        if "env" in attachment["name"].lower():
                            sections = clean_content.split("---")
                            if len(sections) > 2:
                                clean_content = sections[0].strip() + "\n\n" + sections[-1].strip()
                        
                        content.append("\n<details>\n<summary>Content</summary>\n")
                        content.append("\n```markdown")
                        content.append(clean_content)
                        content.append("```\n")
                        content.append("</details>\n")

        # Write content to file
        content_str = "\n".join(content).rstrip()
        if content_str.endswith("%"):
            content_str = content_str[:-1]
        attachments_file.write_text(content_str, encoding="utf-8")

        # Create and save metadata for attachments file
        metadata = FileMetadata.from_file(
            file_path=attachments_file,
            handler_name="split",
            handler_version="1.0",
        )
        metadata.processed = True
        metadata.add_output_file(attachments_file)
        metadata_path = output_dir / "Attachments.metadata.json"
        metadata.save(metadata_path)

        return attachments_file
