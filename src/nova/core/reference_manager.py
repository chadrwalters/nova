"""Reference management system for Nova."""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class Reference:
    """Represents a reference in a document."""

    ref_type: str  # ATTACH, NOTE, etc.
    ref_id: str  # The unique identifier
    source_file: Path  # File containing the reference
    target_file: Optional[Path] = None  # File being referenced
    line_number: Optional[int] = None
    context: Optional[str] = None
    is_valid: bool = False
    section: Optional[str] = None  # Section containing the reference
    file_type: Optional[str] = None  # Standardized file type
    date: Optional[str] = None  # Date extracted from filename


class ReferenceManager:
    """Manages document references and ensures their validity."""

    # File type mapping
    FILE_TYPE_MAP = {
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

    def __init__(self) -> None:
        """Initialize the reference manager."""
        self.logger = logging.getLogger(__name__)
        self.references: Dict[str, Reference] = {}  # ref_marker -> Reference
        self.file_references: Dict[Path, Set[str]] = {}  # file -> set of ref_markers
        self.invalid_references: List[Reference] = []

    def _get_file_type(self, path: Path) -> str:
        """Get standardized file type from path."""
        return self.FILE_TYPE_MAP.get(path.suffix.lower(), "OTHER")

    def _extract_date(self, path: Path) -> Optional[str]:
        """Extract date from file path if available."""
        match = re.search(r"(\d{8})", str(path))
        return match.group(1) if match else None

    def _detect_section(self, content: str, position: int) -> Optional[str]:
        """Detect the section containing a reference.

        Args:
            content: The full content
            position: Position of the reference in content

        Returns:
            Section name if found, None otherwise
        """
        # Find the last heading before this position
        lines = content[:position].split("\n")
        for line in reversed(lines):
            if line.startswith("#"):
                # Remove # symbols and whitespace
                return line.lstrip("#").strip()
        return None

    def extract_references(self, content: str, source_file: Path) -> List[Reference]:
        """Extract all references from content.

        Args:
            content: The content to extract references from
            source_file: The file containing the content

        Returns:
            List of found references
        """
        references = []

        # Reference patterns
        patterns = [
            # Attachment references (with optional ! for images)
            (r"!?\[ATTACH:([^:\]]+):([^\]]+)\]", "ATTACH"),
            # Note references
            (r"\[NOTE:([^\]]+)\]", "NOTE"),
        ]

        # Extract references line by line to get context
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            # Get context (3 lines before and after)
            start = max(0, i - 4)
            end = min(len(lines), i + 3)
            context = "\n".join(lines[start:end])

            # Find references in this line
            for pattern, ref_type in patterns:
                for match in re.finditer(pattern, line):
                    if ref_type == "ATTACH":
                        file_type, ref_id = match.groups()
                        ref_marker = f"[ATTACH:{file_type}:{ref_id}]"
                    else:
                        ref_id = match.group(1)
                        ref_marker = f"[{ref_type}:{ref_id}]"

                    # Create reference object
                    reference = Reference(
                        ref_type=ref_type,
                        ref_id=ref_id,
                        source_file=source_file,
                        line_number=i,
                        context=context,
                        section=self._detect_section(content, match.start()),
                    )

                    # Add file type and date if it's an attachment
                    if ref_type == "ATTACH":
                        if reference.target_file:
                            reference.file_type = self._get_file_type(
                                reference.target_file
                            )
                            reference.date = self._extract_date(reference.target_file)

                    # Store reference
                    self.references[ref_marker] = reference
                    if source_file not in self.file_references:
                        self.file_references[source_file] = set()
                    self.file_references[source_file].add(ref_marker)

                    references.append(reference)

        return references

    def validate_references(self, base_dir: Path) -> List[str]:
        """Validate all references.

        Args:
            base_dir: Base directory for resolving relative paths

        Returns:
            List of validation error messages
        """
        errors = []

        # Check each reference
        for ref_marker, reference in self.references.items():
            if reference.ref_type == "ATTACH":
                # Verify attachment exists
                if not reference.target_file or not reference.target_file.exists():
                    errors.append(
                        f"Invalid attachment reference {ref_marker} in {reference.source_file} "
                        f"at line {reference.line_number}"
                    )
                    self.invalid_references.append(reference)
                    reference.is_valid = False
                else:
                    reference.is_valid = True
                    # Update file type and date
                    reference.file_type = self._get_file_type(reference.target_file)
                    reference.date = self._extract_date(reference.target_file)

            elif reference.ref_type == "NOTE":
                # Verify note section exists
                note_found = False
                if reference.target_file and reference.target_file.exists():
                    try:
                        content = reference.target_file.read_text()
                        if f"## {ref_marker}" in content:
                            note_found = True
                    except Exception as e:
                        self.logger.error(f"Error reading note file: {e}")

                if not note_found:
                    errors.append(
                        f"Invalid note reference {ref_marker} in {reference.source_file} "
                        f"at line {reference.line_number}"
                    )
                    self.invalid_references.append(reference)
                    reference.is_valid = False
                else:
                    reference.is_valid = True

        return errors

    def update_references(self, old_path: Path, new_path: Path) -> None:
        """Update references when a file is moved/renamed.

        Args:
            old_path: Original file path
            new_path: New file path
        """
        # Update references to this file
        for reference in self.references.values():
            if reference.target_file == old_path:
                reference.target_file = new_path
                # Update file type and date
                reference.file_type = self._get_file_type(new_path)
                reference.date = self._extract_date(new_path)

        # Update references from this file
        if old_path in self.file_references:
            self.file_references[new_path] = self.file_references.pop(old_path)

    def get_invalid_references(self) -> List[Reference]:
        """Get list of invalid references.

        Returns:
            List of invalid references
        """
        return self.invalid_references

    def get_file_references(self, file_path: Path) -> List[Reference]:
        """Get all references in a file.

        Args:
            file_path: Path to the file

        Returns:
            List of references in the file
        """
        if file_path not in self.file_references:
            return []

        return [
            self.references[ref_marker]
            for ref_marker in self.file_references[file_path]
        ]

    def cleanup_references(self) -> None:
        """Remove invalid and orphaned references."""
        # Remove invalid references
        for reference in self.invalid_references:
            ref_marker = f"[{reference.ref_type}:{reference.ref_id}]"
            self.references.pop(ref_marker, None)
            if reference.source_file in self.file_references:
                self.file_references[reference.source_file].discard(ref_marker)

        # Remove empty file reference sets
        empty_files = [
            file_path for file_path, refs in self.file_references.items() if not refs
        ]
        for file_path in empty_files:
            self.file_references.pop(file_path)

        self.invalid_references.clear()
