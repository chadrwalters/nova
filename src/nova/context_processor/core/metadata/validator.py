"""Metadata validation."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from .models.base import BaseMetadata
from .store import MetadataStore
from ..errors import ValidationError

logger = logging.getLogger(__name__)

class MetadataValidator:
    """Validator for metadata."""

    def __init__(self, store: MetadataStore):
        """Initialize validator.

        Args:
            store: Metadata store
        """
        self.store = store

    def validate(self, metadata: BaseMetadata) -> List[str]:
        """Validate metadata.

        Args:
            metadata: Metadata to validate

        Returns:
            List of validation errors
        """
        errors = []

        # Validate required fields
        if not metadata.file_path or not isinstance(metadata.file_path, Path):
            errors.append("file_path must be a valid Path")

        if not metadata.file_type:
            errors.append("file_type is required")

        if not metadata.handler_name:
            errors.append("handler_name is required")

        if not metadata.handler_version:
            errors.append("handler_version is required")

        # Validate standardized path if set
        if metadata.standardized_path:
            if not isinstance(metadata.standardized_path, Path):
                errors.append("standardized_path must be a valid Path")
            if metadata.standardized_path.suffix != metadata.file_path.suffix:
                errors.append("standardized_path must have same extension as file_path")

        # Validate output path if set
        if metadata.output_path:
            if not isinstance(metadata.output_path, Path):
                errors.append("output_path must be a valid Path")
            if not metadata.output_path.suffix == ".md":
                errors.append("output_path must have .md extension")

        # Validate dates
        if metadata.document_date and not isinstance(metadata.document_date, datetime):
            errors.append("document_date must be a valid datetime")

        if metadata.created_at and not isinstance(metadata.created_at, datetime):
            errors.append("created_at must be a valid datetime")

        if metadata.modified_at and not isinstance(metadata.modified_at, datetime):
            errors.append("modified_at must be a valid datetime")

        # Validate output files
        for output_file in metadata.output_files:
            if not isinstance(output_file, Path):
                errors.append(f"Invalid output file path: {output_file}")

        # Validate title
        if not metadata.title:
            errors.append("title is required")

        # Log validation results
        if errors:
            logger.warning(f"Validation errors for {metadata.file_path}:")
            for error in errors:
                logger.warning(f"  - {error}")

        return errors

    def validate_related_metadata(self, metadata: BaseMetadata) -> List[str]:
        """Validate metadata against related files.

        Args:
            metadata: Metadata to validate

        Returns:
            List of validation errors
        """
        errors = []

        # Check if file exists
        if not metadata.file_path.exists():
            errors.append(f"File does not exist: {metadata.file_path}")

        # Check output files
        for output_file in metadata.output_files:
            if not output_file.exists():
                errors.append(f"Output file does not exist: {output_file}")

        # Check standardized path
        if metadata.standardized_path and metadata.standardized_path.exists():
            # Compare file sizes
            if metadata.standardized_path.stat().st_size != metadata.file_path.stat().st_size:
                errors.append(f"File size mismatch for standardized path: {metadata.standardized_path}")

        # Check output path
        if metadata.output_path and not metadata.output_path.exists():
            errors.append(f"Output file does not exist: {metadata.output_path}")

        return errors 