"""Reference validation for Nova document processor."""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from ..core.errors import ValidationError
from ..core.metadata import BaseMetadata
from ..core.metadata.store import MetadataStore

logger = logging.getLogger(__name__)


class ReferenceValidator:
    """Validator for document references."""

    def __init__(self, metadata_store: MetadataStore):
        """Initialize validator.

        Args:
            metadata_store: Metadata store instance
        """
        self.metadata_store = metadata_store
        self.note_pattern = re.compile(r'\[NOTE:([^\]]+)\]')
        self.attach_pattern = re.compile(r'\[ATTACH:([^:]+):([^\]]+)\]')

    def validate_references(
        self,
        content: str,
        file_path: Path,
        metadata: Optional[BaseMetadata] = None
    ) -> List[ValidationError]:
        """Validate document references.

        Args:
            content: Document content
            file_path: Path to source file
            metadata: Optional metadata for additional validation

        Returns:
            List of validation errors
        """
        errors = []

        try:
            # Validate note references
            note_errors = self._validate_note_references(content, file_path)
            errors.extend(note_errors)

            # Validate attachment references
            attach_errors = self._validate_attachment_references(content, file_path, metadata)
            errors.extend(attach_errors)

            # Check for circular references
            if metadata:
                circular_errors = self._check_circular_references(metadata, set())
                errors.extend(circular_errors)

            return errors

        except Exception as e:
            errors.append(ValidationError(
                message=f"Reference validation failed: {str(e)}",
                file_path=file_path,
                details={"error": str(e)},
                recovery_hint="Check reference syntax and targets."
            ))
            return errors

    def _validate_note_references(self, content: str, file_path: Path) -> List[ValidationError]:
        """Validate note references.

        Args:
            content: Document content
            file_path: Path to source file

        Returns:
            List of validation errors
        """
        errors = []
        notes = set(self.note_pattern.findall(content))

        for note_id in notes:
            # Check note ID format
            if not self._is_valid_note_id(note_id):
                errors.append(ValidationError(
                    message=f"Invalid note ID format: {note_id}",
                    file_path=file_path,
                    details={"note_id": note_id},
                    recovery_hint="Note IDs should be in YYYYMMDD-description format."
                ))
                continue

            # Check if note exists
            note_path = self._get_note_path(note_id)
            if not note_path.exists():
                errors.append(ValidationError(
                    message=f"Missing note: {note_id}",
                    file_path=file_path,
                    details={
                        "note_id": note_id,
                        "expected_path": str(note_path)
                    },
                    recovery_hint="Create the missing note or update the reference."
                ))

        return errors

    def _validate_attachment_references(
        self,
        content: str,
        file_path: Path,
        metadata: Optional[BaseMetadata]
    ) -> List[ValidationError]:
        """Validate attachment references.

        Args:
            content: Document content
            file_path: Path to source file
            metadata: Optional metadata for additional validation

        Returns:
            List of validation errors
        """
        errors = []
        attachments = self.attach_pattern.findall(content)

        for attach_type, attach_id in attachments:
            # Check attachment ID format
            if not self._is_valid_attachment_id(attach_id):
                errors.append(ValidationError(
                    message=f"Invalid attachment ID format: {attach_id}",
                    file_path=file_path,
                    details={
                        "attachment_type": attach_type,
                        "attachment_id": attach_id
                    },
                    recovery_hint="Attachment IDs should be in YYYYMMDD-description format."
                ))
                continue

            # Check if attachment exists
            attach_path = self._get_attachment_path(attach_type, attach_id)
            if not attach_path.exists():
                errors.append(ValidationError(
                    message=f"Missing attachment: {attach_type}:{attach_id}",
                    file_path=file_path,
                    details={
                        "attachment_type": attach_type,
                        "attachment_id": attach_id,
                        "expected_path": str(attach_path)
                    },
                    recovery_hint="Add the missing attachment or update the reference."
                ))
                continue

            # Check if attachment is tracked in metadata
            if metadata and hasattr(metadata, "attachments"):
                if str(attach_path) not in metadata.attachments:
                    errors.append(ValidationError(
                        message=f"Untracked attachment: {attach_type}:{attach_id}",
                        file_path=file_path,
                        details={
                            "attachment_type": attach_type,
                            "attachment_id": attach_id,
                            "attachment_path": str(attach_path)
                        },
                        recovery_hint="Add the attachment to metadata tracking."
                    ))

        return errors

    def _check_circular_references(
        self,
        metadata: BaseMetadata,
        visited: Set[Path],
        depth: int = 0
    ) -> List[ValidationError]:
        """Check for circular references.

        Args:
            metadata: Current metadata
            visited: Set of visited files
            depth: Current recursion depth

        Returns:
            List of validation errors
        """
        errors = []
        max_depth = 10  # Maximum allowed reference depth

        if depth > max_depth:
            errors.append(ValidationError(
                message="Reference chain too deep",
                file_path=metadata.file_path,
                details={"max_depth": max_depth},
                recovery_hint="Simplify reference structure."
            ))
            return errors

        file_path = Path(metadata.file_path)
        if file_path in visited:
            errors.append(ValidationError(
                message="Circular reference detected",
                file_path=metadata.file_path,
                details={"reference_chain": [str(p) for p in visited]},
                recovery_hint="Remove circular reference."
            ))
            return errors

        visited.add(file_path)

        try:
            # Check parent references
            if hasattr(metadata, "parent_file"):
                parent_path = Path(metadata.parent_file)
                parent_metadata = self.metadata_store.load(parent_path)
                if parent_metadata:
                    parent_errors = self._check_circular_references(
                        parent_metadata,
                        visited.copy(),
                        depth + 1
                    )
                    errors.extend(parent_errors)

            # Check attachment references
            if hasattr(metadata, "attachments"):
                for attachment in metadata.attachments:
                    attachment_path = Path(attachment)
                    attachment_metadata = self.metadata_store.load(attachment_path)
                    if attachment_metadata:
                        attachment_errors = self._check_circular_references(
                            attachment_metadata,
                            visited.copy(),
                            depth + 1
                        )
                        errors.extend(attachment_errors)

            return errors

        except Exception as e:
            errors.append(ValidationError(
                message=f"Circular reference check failed: {str(e)}",
                file_path=metadata.file_path,
                details={"error": str(e)},
                recovery_hint="Check reference structure."
            ))
            return errors

    def _is_valid_note_id(self, note_id: str) -> bool:
        """Check if note ID format is valid.

        Args:
            note_id: Note ID to check

        Returns:
            bool: True if valid, False otherwise
        """
        # Format: YYYYMMDD-description
        pattern = r'^\d{8}-[a-z0-9-]+$'
        return bool(re.match(pattern, note_id))

    def _is_valid_attachment_id(self, attach_id: str) -> bool:
        """Check if attachment ID format is valid.

        Args:
            attach_id: Attachment ID to check

        Returns:
            bool: True if valid, False otherwise
        """
        # Format: YYYYMMDD-description
        pattern = r'^\d{8}-[a-z0-9-]+$'
        return bool(re.match(pattern, attach_id))

    def _get_note_path(self, note_id: str) -> Path:
        """Get expected path for a note.

        Args:
            note_id: Note ID

        Returns:
            Path: Expected note path
        """
        return self.metadata_store.base_dir / "_NovaProcessing" / "notes" / f"{note_id}.md"

    def _get_attachment_path(self, attach_type: str, attach_id: str) -> Path:
        """Get expected path for an attachment.

        Args:
            attach_type: Attachment type
            attach_id: Attachment ID

        Returns:
            Path: Expected attachment path
        """
        return self.metadata_store.base_dir / "_NovaProcessing" / "attachments" / attach_type / f"{attach_id}" 