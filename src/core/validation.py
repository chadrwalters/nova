"""Validation utilities for markdown processing."""

import os
from pathlib import Path
from typing import Set

from .config import NovaConfig
from .errors import ValidationError
from .logging import get_logger

logger = get_logger(__name__)

class InputValidator:
    """Validates input files and environment."""

    def __init__(self, config: NovaConfig):
        self.config = config
        self._allowed_extensions = self._get_allowed_extensions()

    def _get_allowed_extensions(self) -> Set[str]:
        """Get set of allowed file extensions."""
        markdown_exts = {'.md', '.markdown'}
        office_exts = {'.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls', '.pdf'}
        return markdown_exts | office_exts

    def validate_file(self, file_path: Path) -> None:
        """Validate a single input file."""
        if not file_path.exists():
            raise ValidationError(f"File does not exist: {file_path}")

        if not file_path.is_file():
            raise ValidationError(f"Not a file: {file_path}")

        # Check file size
        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > self.config.processing.max_file_size:
            raise ValidationError(
                f"File exceeds size limit: {size_mb}MB > {self.config.processing.max_file_size}MB"
            )

        # Check extension
        if file_path.suffix.lower() not in self._allowed_extensions:
            raise ValidationError(
                f"Unsupported file type: {file_path.suffix}. "
                f"Supported types: {', '.join(self._allowed_extensions)}"
            )

    def validate_directory(self, dir_path: Path) -> None:
        """Validate input directory."""
        if not dir_path.exists():
            raise ValidationError(f"Directory does not exist: {dir_path}")

        if not dir_path.is_dir():
            raise ValidationError(f"Not a directory: {dir_path}")

        # Check total size
        total_size_mb = sum(
            f.stat().st_size for f in dir_path.rglob("*") if f.is_file()
        ) / (1024 * 1024)

        if total_size_mb > self.config.processing.max_total_size:
            raise ValidationError(
                f"Total size exceeds limit: {total_size_mb}MB > "
                f"{self.config.processing.max_total_size}MB"
            )

    def validate_environment(self) -> None:
        """Validate required environment variables."""
        required_vars = [
            "NOVA_BASE_DIR",
            "NOVA_INPUT_DIR",
            "NOVA_PROCESSING_DIR",
            "NOVA_PHASE_MARKDOWN_PARSE",
            "NOVA_TEMP_DIR",
            "NOVA_OFFICE_TEMP_DIR"
        ]

        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValidationError(f"Missing environment variables: {', '.join(missing)}")