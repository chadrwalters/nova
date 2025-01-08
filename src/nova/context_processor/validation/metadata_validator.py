"""Metadata validation for Nova document processor."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..core.errors import ValidationError
from ..core.metadata import BaseMetadata
from ..core.metadata.store import MetadataStore

logger = logging.getLogger(__name__)


class MetadataValidator:
    """Validates metadata for Nova document processor."""

    def __init__(self, store: MetadataStore) -> None:
        """Initialize metadata validator.

        Args:
            store: Metadata store to use for validation
        """
        self.store = store

    def validate_file_path(self, file_path: Path) -> List[str]:
        """Validate a file path.

        Args:
            file_path: Path to validate

        Returns:
            List of validation errors
        """
        errors = []

        try:
            # Check if path is absolute
            if file_path.is_absolute():
                errors.append("File path must be relative")

            # Check for invalid characters
            invalid_chars = '<>:"|?*'
            if any(c in str(file_path) for c in invalid_chars):
                errors.append("File path contains invalid characters")

            # Check path length
            if len(str(file_path)) > 255:
                errors.append("File path is too long")

            # Check if parent directory exists
            if not file_path.parent.exists():
                errors.append("Parent directory does not exist")

            return errors
        except Exception as e:
            return [f"File path validation failed: {str(e)}"]

    def validate_metadata(self, metadata: BaseMetadata) -> List[str]:
        """Validate metadata.

        Args:
            metadata: Metadata to validate

        Returns:
            List of validation errors
        """
        errors = []

        try:
            # Basic metadata validation
            if not metadata.file_path:
                errors.append("Missing file path")
            if not metadata.file_type:
                errors.append("Missing file type")
            if metadata.file_size < 0:
                errors.append("Invalid file size")

            # Validate file path if present
            if metadata.file_path:
                path_errors = self.validate_file_path(metadata.file_path)
                errors.extend(path_errors)

            # Validate output files if present
            if metadata.output_files:
                for output_file in metadata.output_files:
                    output_path = Path(output_file)
                    path_errors = self.validate_file_path(output_path)
                    if path_errors:
                        errors.append(f"Invalid output file path: {output_file}")
                        errors.extend(path_errors)

            return errors
        except Exception as e:
            return [f"Metadata validation failed: {str(e)}"]

    def validate_cross_phase(self, file_path: Path, phases: List[str]) -> List[str]:
        """Validate metadata across phases.

        Args:
            file_path: Path to file
            phases: List of phases to validate

        Returns:
            List of validation errors
        """
        errors = []

        try:
            # Get metadata for each phase
            phase_metadata = {}
            for phase in phases:
                metadata = self.store.get(file_path, phase)
                if metadata:
                    phase_metadata[phase] = metadata

            if not phase_metadata:
                return ["No metadata found for any phase"]

            # Validate version progression
            last_version = None
            for phase in phases:
                if phase in phase_metadata:
                    current_version = phase_metadata[phase].current_version
                    if last_version:
                        if current_version.major < last_version.major:
                            errors.append(
                                f"Invalid version progression in {phase}: "
                                f"major version decreased from {last_version} to {current_version}"
                            )
                        elif current_version.minor < last_version.minor and current_version.major == last_version.major:
                            errors.append(
                                f"Invalid version progression in {phase}: "
                                f"minor version decreased from {last_version} to {current_version}"
                            )
                    last_version = current_version

            # Validate consistency across phases
            base_metadata = phase_metadata[phases[0]]
            for phase in phases[1:]:
                if phase in phase_metadata:
                    current = phase_metadata[phase]
                    # Check immutable fields
                    if current.file_path != base_metadata.file_path:
                        errors.append(f"File path mismatch in {phase}")
                    if current.file_type != base_metadata.file_type:
                        errors.append(f"File type mismatch in {phase}")
                    if current.file_size != base_metadata.file_size:
                        errors.append(f"File size mismatch in {phase}")

                    # Check phase-specific requirements
                    if phase == "parse":
                        if not current.metadata.get("original_path"):
                            errors.append("Missing original path in parse phase")
                    elif phase == "disassemble":
                        if not current.output_files:
                            errors.append("Missing output files in disassemble phase")
                    elif phase == "split":
                        if not current.output_files:
                            errors.append("Missing output files in split phase")
                        if not current.metadata.get("references"):
                            errors.append("Missing references in split phase")

                    # Validate related metadata
                    if current.metadata.get("embedded_files"):
                        for embedded_file in current.metadata["embedded_files"]:
                            embedded_metadata = self.store.get(Path(embedded_file), phase)
                            if not embedded_metadata:
                                errors.append(f"Missing metadata for embedded file {embedded_file} in {phase}")

                    # Validate output files
                    if current.output_files:
                        for output_file in current.output_files:
                            output_path = Path(output_file)
                            if not output_path.exists():
                                errors.append(f"Missing output file {output_file} in {phase}")

            return errors
        except Exception as e:
            return [f"Cross-phase validation failed: {str(e)}"] 