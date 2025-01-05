"""Processor for markdown content."""

import json
import logging
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

from ..core.reference_manager import ReferenceManager


class MarkdownProcessor:
    """Processor for markdown content."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.reference_manager = ReferenceManager()

    def _is_text_file(self, path: str) -> bool:
        """Check if a file is a text file based on extension."""
        text_extensions = {
            ".txt",
            ".md",
            ".json",
            ".csv",
            ".html",
            ".xml",
            ".yml",
            ".yaml",
        }
        return Path(path).suffix.lower() in text_extensions

    def _extract_attachments(
        self, content: str, source_file: str
    ) -> List[Dict[str, Any]]:
        """Extract attachments from markdown content.

        Args:
            content: The markdown content to process
            source_file: The source file path

        Returns:
            List of attachment dictionaries containing metadata and paths
        """
        attachments = []

        # Extract references using ReferenceManager
        references = self.reference_manager.extract_references(
            content, Path(source_file)
        )

        # Convert references to attachments
        for reference in references:
            if reference.ref_type == "ATTACH":
                # Build attachment info
                attachment = {
                    "path": str(reference.target_file)
                    if reference.target_file
                    else reference.ref_id,
                    "text": reference.ref_id,
                    "context": reference.context,
                    "section": "attachments",  # Default to attachments section
                    "source_file": source_file,
                    "date": self._extract_date(source_file),
                    "type": reference.ref_id.split(":")[0]
                    if ":" in reference.ref_id
                    else "OTHER",
                    "is_image": reference.ref_id.startswith("!"),
                    "ref": f"[ATTACH:{reference.ref_id}]",
                }

                attachments.append(attachment)

        return attachments

    def _extract_date(self, file_path: str) -> str:
        """Extract date from file path if available."""
        match = re.search(r"(\d{8})", str(file_path))
        return match.group(1) if match else "unknown"

    def _get_file_type(self, path: str) -> str:
        """Get standardized file type from path."""
        ext = Path(path).suffix.lower()
        type_map = {
            ".pdf": "PDF",
            ".doc": "DOC",
            ".docx": "DOC",
            ".jpg": "JPG",
            ".jpeg": "JPG",
            ".png": "PNG",
            ".heic": "JPG",
            ".xlsx": "EXCEL",
            ".xls": "EXCEL",
            ".csv": "EXCEL",
            ".txt": "TXT",
            ".json": "JSON",
            ".html": "DOC",
            ".md": "DOC",
        }
        return type_map.get(ext, "OTHER")

    def _build_attachments_markdown(self, attachments: List[Dict[str, Any]]) -> str:
        """Build a markdown string containing all attachments with their context.

        Args:
            attachments: List of attachment dictionaries containing metadata and paths

        Returns:
            A markdown string containing all attachments organized by type
        """
        if not attachments:
            return "# Attachments\n\nNo attachments found."

        # Group attachments by date and type
        by_date = defaultdict(lambda: defaultdict(list))
        for attachment in attachments:
            date = self._extract_date(attachment["source_file"])
            file_type = attachment["type"]
            by_date[date][file_type].append(attachment)

        # Build the markdown content
        content = ["# Attachments"]

        for date in sorted(by_date.keys()):
            content.append(f"\n## {date}")

            for file_type in sorted(by_date[date].keys()):
                content.append(f"\n### {file_type} Files\n")

                for attachment in sorted(
                    by_date[date][file_type], key=lambda x: x["text"]
                ):
                    # Use the reference marker
                    content.append(f"#### {attachment['ref']}\n")

                    # Add context if available
                    if attachment["context"]:
                        content.append("Context:")
                        # Context is already processed by ReferenceManager
                        for line in attachment["context"].split("\n"):
                            content.append(f"> {line}")
                        content.append("")  # Add a blank line after context

                    # Add source information
                    source_info = [
                        f"From {os.path.basename(attachment['source_file'])}"
                    ]
                    if attachment["section"]:
                        source_info.append(
                            f"in {attachment['section'].title()} section"
                        )
                    content.append(f"Source: {', '.join(source_info)}\n")

        return "\n".join(content)
