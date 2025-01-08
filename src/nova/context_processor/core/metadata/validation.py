"""Metadata validation system."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Type
from pydantic import ValidationError
import json

from .models.base import BaseMetadata
from .models.types import (
    AudioMetadata,
    ArchiveMetadata,
    DocumentMetadata,
    HTMLMetadata,
    ImageMetadata,
    MarkdownMetadata,
    SpreadsheetMetadata,
    VideoMetadata,
)
from .store.manager import MetadataStore


logger = logging.getLogger(__name__)


class MetadataValidator:
    """Validator for metadata objects."""

    def __init__(self, metadata_store: MetadataStore):
        """Initialize validator.

        Args:
            metadata_store: Metadata store instance
        """
        self.store = metadata_store
        self.errors: List[str] = []

    def validate_schema(self, metadata: BaseMetadata) -> List[str]:
        """Validate metadata against its schema.

        Args:
            metadata: Metadata object to validate

        Returns:
            List of validation error messages
        """
        errors = []
        try:
            # Validate using Pydantic model
            metadata_class = type(metadata)
            metadata_class.model_validate(metadata.model_dump())

            # Additional type-specific validation
            if isinstance(metadata, ImageMetadata):
                errors.extend(self._validate_image_metadata(metadata))
            elif isinstance(metadata, DocumentMetadata):
                errors.extend(self._validate_document_metadata(metadata))
            elif isinstance(metadata, MarkdownMetadata):
                errors.extend(self._validate_markdown_metadata(metadata))
            elif isinstance(metadata, ArchiveMetadata):
                errors.extend(self._validate_archive_metadata(metadata))

        except ValidationError as e:
            errors.extend(str(error) for error in e.errors())

        return errors

    def validate_cross_phase(self, file_path: Path, phases: List[str]) -> List[str]:
        """Validate metadata across processing phases.

        Args:
            file_path: Path to file
            phases: List of phases to validate

        Returns:
            List of validation error messages
        """
        errors = []
        phase_metadata = {}

        # Get metadata for each phase
        for phase in phases:
            metadata = self.store.get(file_path, phase)
            if metadata:
                phase_metadata[phase] = metadata

        if not phase_metadata:
            # Try to find metadata in any of the expected locations
            metadata_found = False
            for phase in phases:
                metadata_path = self.store._get_metadata_path(file_path, phase)
                if metadata_path.exists():
                    try:
                        with open(metadata_path, "r", encoding="utf-8") as f:
                            metadata = json.load(f)
                            metadata_found = True
                            break
                    except Exception as e:
                        errors.append(f"Error reading metadata file {metadata_path}: {str(e)}")

            if not metadata_found:
                errors.append(f"No metadata found for {file_path} in any phase")
                errors.append(f"Checked phases: {', '.join(phases)}")
                errors.append(f"Checked locations:")
                for phase in phases:
                    errors.append(f"  - {self.store._get_metadata_path(file_path, phase)}")
            return errors

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
                        if not Path(output_file).exists():
                            errors.append(f"Missing output file {output_file} in {phase}")

        return errors

    def validate_related_metadata(self, metadata: BaseMetadata) -> List[str]:
        """Validate relationships between metadata objects.

        Args:
            metadata: Metadata object to validate

        Returns:
            List of validation error messages
        """
        errors = []

        # Check embedded files in markdown metadata
        if isinstance(metadata, MarkdownMetadata):
            for embedded_file in metadata.embedded_files:
                embedded_metadata = self.store.get(embedded_file, "parse")
                if not embedded_metadata:
                    errors.append(f"Missing metadata for embedded file: {embedded_file}")

        # Check archive contents
        if isinstance(metadata, ArchiveMetadata):
            for file_info in metadata.contents:
                if "path" in file_info:
                    file_path = Path(file_info["path"])
                    file_metadata = self.store.get(file_path, "parse")
                    if not file_metadata:
                        errors.append(f"Missing metadata for archive content: {file_path}")

        return errors

    def _validate_image_metadata(self, metadata: ImageMetadata) -> List[str]:
        """Validate image-specific metadata.

        Args:
            metadata: Image metadata to validate

        Returns:
            List of validation error messages
        """
        errors = []

        # Validate dimensions
        if metadata.width is not None and metadata.width <= 0:
            errors.append("Invalid image width")
        if metadata.height is not None and metadata.height <= 0:
            errors.append("Invalid image height")

        # Validate DPI
        if metadata.dpi is not None:
            x_dpi, y_dpi = metadata.dpi
            if x_dpi <= 0 or y_dpi <= 0:
                errors.append("Invalid DPI values")

        # Validate format consistency
        if metadata.has_alpha and metadata.mode not in ("RGBA", "LA"):
            errors.append("Alpha channel indicated but mode is not RGBA/LA")

        return errors

    def _validate_document_metadata(self, metadata: DocumentMetadata) -> List[str]:
        """Validate document-specific metadata.

        Args:
            metadata: Document metadata to validate

        Returns:
            List of validation error messages
        """
        errors = []

        # Validate page count
        if metadata.page_count is not None and metadata.page_count <= 0:
            errors.append("Invalid page count")

        # Validate word count
        if metadata.word_count is not None and metadata.word_count < 0:
            errors.append("Invalid word count")

        # Validate sections
        if metadata.sections:
            for section in metadata.sections:
                if "title" not in section:
                    errors.append("Missing section title")
                if "content" not in section:
                    errors.append("Missing section content")

        return errors

    def _validate_markdown_metadata(self, metadata: MarkdownMetadata) -> List[str]:
        """Validate markdown-specific metadata.

        Args:
            metadata: Markdown metadata to validate

        Returns:
            List of validation error messages
        """
        errors = []

        # Validate headings structure
        if metadata.headings:
            current_level = 0
            for heading in metadata.headings:
                if "level" not in heading or "text" not in heading:
                    errors.append("Invalid heading structure")
                    continue
                # Check heading level progression
                if heading["level"] > current_level + 1:
                    errors.append(f"Invalid heading level progression: {heading}")
                current_level = heading["level"]

        # Validate links
        if metadata.links:
            for link in metadata.links:
                if "text" not in link or "url" not in link:
                    errors.append("Invalid link structure")

        return errors

    def _validate_archive_metadata(self, metadata: ArchiveMetadata) -> List[str]:
        """Validate archive-specific metadata.

        Args:
            metadata: Archive metadata to validate

        Returns:
            List of validation error messages
        """
        errors = []

        # Validate file count
        if metadata.file_count is not None:
            if metadata.file_count <= 0:
                errors.append("Invalid file count")
            if len(metadata.contents) != metadata.file_count:
                errors.append("File count mismatch with contents")

        # Validate total size
        if metadata.total_size is not None and metadata.total_size < metadata.file_size:
            errors.append("Total uncompressed size smaller than compressed size")

        # Validate contents
        for item in metadata.contents:
            if "path" not in item or "size" not in item:
                errors.append("Invalid archive content structure")

        return errors 