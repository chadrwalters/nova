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
        extensions = set()
        
        # Add markdown extensions
        if self.config.processors['markdown'].enabled:
            extensions.update(self.config.processors['markdown'].extensions)
            
        # Add image extensions
        if self.config.processors['image'].enabled:
            extensions.update(self.config.processors['image'].extensions)
            
        # Add office document extensions
        if self.config.processors['office'].enabled:
            extensions.update(self.config.processors['office'].extensions)
            
        return extensions

    def validate_directory(self, directory: Path) -> None:
        """Validate input directory.
        
        Args:
            directory: Directory to validate
            
        Raises:
            ValidationError: If validation fails
        """
        if not directory.exists():
            raise ValidationError(f"Directory does not exist: {directory}")
            
        if not directory.is_dir():
            raise ValidationError(f"Not a directory: {directory}")
            
        # Check for at least one valid file
        has_valid_file = False
        for file_path in directory.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self._allowed_extensions:
                has_valid_file = True
                break
                
        if not has_valid_file:
            raise ValidationError(
                f"No valid files found in {directory}. "
                f"Allowed extensions: {', '.join(sorted(self._allowed_extensions))}"
            )

    def validate_environment(self) -> None:
        """Validate environment variables and paths.
        
        Raises:
            ValidationError: If validation fails
        """
        # Check required environment variables
        required_vars = {
            'NOVA_BASE_DIR',
            'NOVA_INPUT_DIR',
            'NOVA_OUTPUT_DIR',
            'NOVA_PROCESSING_DIR',
            'NOVA_TEMP_DIR',
            'NOVA_PHASE_MARKDOWN_PARSE'
        }
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValidationError(f"Missing required environment variables: {', '.join(missing_vars)}")
            
        # Check directory permissions
        for var in required_vars:
            path = Path(os.getenv(var))
            if path.exists() and not os.access(path, os.W_OK):
                raise ValidationError(f"No write permission for {var}: {path}") 