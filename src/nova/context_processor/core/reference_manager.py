"""Reference management system for Nova."""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
import os


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
    offset: Optional[int] = None  # Character offset in the source file
    length: Optional[int] = None  # Length of the reference in characters
    pointer_id: Optional[int] = None  # ID of the object pointer if this is a pointer reference


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
        self.offset_map: Dict[Path, Dict[int, str]] = defaultdict(dict)
        self.pointer_map: Dict[int, Reference] = {}  # pointer_id -> Reference

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

    def _validate_pointer(self, pointer_id: int, offset: int) -> bool:
        """Validate an object pointer.

        Args:
            pointer_id: ID of the pointer to validate
            offset: Character offset where the pointer was found

        Returns:
            True if the pointer is valid, False otherwise
        """
        # Check if pointer ID is valid (positive and even)
        if pointer_id <= 0 or pointer_id % 2 != 0:
            return False

        # Check if offset is valid (non-negative)
        if offset < 0:
            return False

        # Check if pointer already exists
        if pointer_id in self.pointer_map:
            existing_ref = self.pointer_map[pointer_id]
            # Don't allow duplicate pointers at offset 0
            if offset == 0:
                if existing_ref.offset == 0:
                    self.logger.warning(
                        f"Duplicate pointer {pointer_id} at offset 0 in {existing_ref.source_file}"
                    )
                    return False
                # If existing pointer is not at offset 0, this one takes precedence
                if existing_ref.offset > 0:
                    self.logger.info(
                        f"Pointer {pointer_id} at offset 0 takes precedence over existing pointer at offset {existing_ref.offset}"
                    )
                    return True
            # Don't allow duplicate pointers at any offset
            if offset == existing_ref.offset:
                self.logger.warning(
                    f"Duplicate pointer {pointer_id} at offset {offset} in {existing_ref.source_file}"
                )
                return False

        # Check if pointer ID is in a valid range (e.g., 2-1000)
        if pointer_id > 1000:
            return False

        return True

    def _encode_ref_id(self, ref_id: str) -> str:
        """Encode reference ID to handle special characters.

        Args:
            ref_id: Original reference ID

        Returns:
            Encoded reference ID
        """
        # Replace spaces with underscores for storage
        return ref_id.replace(" ", "_")

    def _decode_ref_id(self, ref_id: str) -> str:
        """Decode reference ID back to original form.

        Args:
            ref_id: Encoded reference ID

        Returns:
            Decoded reference ID
        """
        # Replace underscores with spaces for display
        return ref_id.replace("_", " ")

    def extract_references(self, content: str, source_file: Path) -> List[Reference]:
        """Extract references from content.

        Args:
            content: Content to extract references from
            source_file: Path to file being processed

        Returns:
            List of extracted references
        """
        references = []
        current_offset = 0

        # Track pointers at offset 0 for this file
        offset_zero_pointers = set()

        for i, line in enumerate(content.splitlines(), 1):
            # Find all references in this line
            for match in re.finditer(r'\[([^:]+):([^\]]+)\]', line):
                ref_type = match.group(1)
                ref_length = len(match.group(0))
                abs_offset = current_offset + match.start()
                context = line.strip()

                if ref_type == "POINTER":
                    # Extract pointer ID
                    pointer_id = int(match.group(2))
                    
                    # Skip invalid pointers
                    if not self._validate_pointer(pointer_id, abs_offset):
                        # Only log warning if it's at offset 0
                        if abs_offset == 0:
                            if pointer_id in offset_zero_pointers:
                                self.logger.warning(
                                    f"Duplicate pointer {pointer_id} at offset 0 in {source_file}"
                                )
                            else:
                                self.logger.warning(
                                    f"Invalid pointer {pointer_id} at offset 0 in {source_file}"
                                )
                                offset_zero_pointers.add(pointer_id)
                            continue

                        # Create reference object
                        reference = Reference(
                            ref_type=ref_type,
                            ref_id=str(pointer_id),
                            source_file=source_file,
                            line_number=i,
                            context=context,
                            section=self._detect_section(content, abs_offset),
                            offset=abs_offset,
                            length=ref_length,
                            pointer_id=pointer_id,
                        )

                        # If this is a pointer at offset 0, it takes precedence
                        if abs_offset == 0:
                            # Remove any existing pointers with this ID
                            if pointer_id in self.pointer_map:
                                existing_ref = self.pointer_map[pointer_id]
                                # Remove from invalid references if it was there
                                if existing_ref in self.invalid_references:
                                    self.invalid_references.remove(existing_ref)
                                # Remove from file references
                                if existing_ref.source_file in self.file_references:
                                    ref_marker = f"[POINTER:{existing_ref.pointer_id}]"
                                    self.file_references[existing_ref.source_file].discard(ref_marker)
                                # Remove from offset map
                                if existing_ref.source_file in self.offset_map and existing_ref.offset is not None:
                                    self.offset_map[existing_ref.source_file].pop(existing_ref.offset, None)

                        # Store pointer reference
                        self.pointer_map[pointer_id] = reference
                        offset_zero_pointers.add(pointer_id)

                    else:
                        # Handle ATTACH and NOTE references
                        if ref_type == "ATTACH":
                            file_type, ref_id = match.groups()
                            ref_marker = f"[ATTACH:{file_type}:{ref_id}]"
                        else:
                            ref_id = match.group(2).strip()  # Strip whitespace from note text
                            ref_marker = f"[NOTE:{ref_id}]"

                        # Create reference object
                        reference = Reference(
                            ref_type=ref_type,
                            ref_id=ref_id,
                            source_file=source_file,
                            line_number=i,
                            context=context,
                            section=self._detect_section(content, abs_offset),
                            offset=abs_offset,
                            length=ref_length,
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

                        # Store offset mapping
                        self.offset_map[source_file][abs_offset] = ref_marker

                    references.append(reference)

            # Update offset for next line
            current_offset += len(line) + 1  # +1 for newline

        return references

    def _truncate_content(self, content: str, max_length: int = 100) -> str:
        """Truncate content for error messages.
        
        Args:
            content: Content to truncate
            max_length: Maximum length before truncation
            
        Returns:
            Truncated content with ellipsis if needed
        """
        if not content:
            return ""
        if len(content) <= max_length:
            return content
        return content[:max_length] + "..."

    def _normalize_path(self, path: str) -> str:
        """Normalize a path for comparison.

        Args:
            path: Path to normalize

        Returns:
            Normalized path string
        """
        # Convert to lowercase for case-insensitive comparison
        normalized = path.lower()
        # Replace backslashes with forward slashes
        normalized = normalized.replace('\\', '/')
        # Remove any leading/trailing whitespace
        normalized = normalized.strip()
        return normalized

    def _fuzzy_match_path(self, target: str, candidates: List[str]) -> Optional[str]:
        """Find best matching path using fuzzy matching.

        Args:
            target: Target path to match
            candidates: List of candidate paths

        Returns:
            Best matching path or None if no good match found
        """
        # Normalize target and candidates
        target_norm = self._normalize_path(target)
        candidates_norm = [(c, self._normalize_path(c)) for c in candidates]
        
        # First try exact match with normalized paths
        for orig, norm in candidates_norm:
            if norm == target_norm:
                return orig
            
        # Try matching without extension
        target_no_ext = os.path.splitext(target_norm)[0]
        for orig, norm in candidates_norm:
            if os.path.splitext(norm)[0] == target_no_ext:
                return orig
            
        # Try partial path matching
        target_parts = target_norm.split('/')
        best_match = None
        best_score = 0
        
        for orig, norm in candidates_norm:
            norm_parts = norm.split('/')
            score = sum(1 for t, n in zip(reversed(target_parts), reversed(norm_parts)) if t == n)
            if score > best_score:
                best_score = score
                best_match = orig
            
        # Return best match only if it matches at least the filename
        if best_score > 0:
            return best_match
        return None

    def validate_references(self, base_dir: Path) -> List[str]:
        """Validate all collected references.

        Args:
            base_dir: Base directory for resolving relative paths

        Returns:
            List of validation error messages
        """
        errors = []
        
        # Get list of all files in base directory
        all_files = []
        for root, _, files in os.walk(base_dir):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), base_dir)
                all_files.append(rel_path)

        # Validate each reference
        for ref in self.references:
            if ref.ref_type == "ATTACH":
                # Try to find matching file
                target_path = ref.ref_id
                if not os.path.isabs(target_path):
                    # For relative paths, try both as-is and relative to source file
                    source_dir = os.path.dirname(ref.source_file)
                    candidates = [
                        target_path,
                        os.path.join(source_dir, target_path)
                    ]
                    
                    # Try fuzzy matching
                    match = None
                    for candidate in candidates:
                        match = self._fuzzy_match_path(candidate, all_files)
                        if match:
                            break
                        
                    if not match:
                        errors.append(
                            f"Invalid attachment reference in {ref.source_file}: "
                            f"[ATTACH:{ref.ref_id}] - No matching file found"
                        )
                else:
                    # For absolute paths, verify existence
                    if not os.path.exists(target_path):
                        errors.append(
                            f"Invalid attachment reference in {ref.source_file}: "
                            f"[ATTACH:{ref.ref_id}] - File not found"
                        )

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

        # Update offset map
        if old_path in self.offset_map:
            self.offset_map[new_path] = self.offset_map.pop(old_path)

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

    def get_reference_at_offset(self, file_path: Path, offset: int) -> Optional[Reference]:
        """Get reference at a specific offset in a file.

        Args:
            file_path: Path to the file
            offset: Character offset in the file

        Returns:
            Reference at the offset if found, None otherwise
        """
        if file_path not in self.offset_map:
            return None

        if offset not in self.offset_map[file_path]:
            return None

        ref_marker = self.offset_map[file_path][offset]
        return self.references.get(ref_marker)

    def cleanup_references(self) -> None:
        """Remove invalid and orphaned references."""
        # Remove invalid references
        for reference in self.invalid_references:
            ref_marker = f"[{reference.ref_type}:{reference.ref_id}]"
            self.references.pop(ref_marker, None)
            if reference.source_file in self.file_references:
                self.file_references[reference.source_file].discard(ref_marker)
            if reference.source_file in self.offset_map:
                if reference.offset is not None:
                    self.offset_map[reference.source_file].pop(reference.offset, None)
            if reference.pointer_id is not None:
                self.pointer_map.pop(reference.pointer_id, None)

        # Remove empty file reference sets
        empty_files = [
            file_path for file_path, refs in self.file_references.items() if not refs
        ]
        for file_path in empty_files:
            self.file_references.pop(file_path)
            self.offset_map.pop(file_path, None)

        self.invalid_references.clear()
