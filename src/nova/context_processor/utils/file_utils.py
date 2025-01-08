"""File utilities for Nova document processor."""

import hashlib
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def calculate_file_hash(file_path: Path) -> Optional[str]:
    """Calculate SHA-256 hash of file contents.

    Args:
        file_path: Path to file

    Returns:
        Optional[str]: Hash string if successful, None otherwise
    """
    try:
        # Create hash object
        hasher = hashlib.sha256()

        # Read file in chunks
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)

        # Return hex digest
        return hasher.hexdigest()

    except Exception as e:
        logger.error(f"Failed to calculate hash for {file_path}: {e}")
        return None


def standardize_filename(filename: str) -> str:
    """Standardize filename by removing invalid characters and spaces.

    Args:
        filename: Original filename

    Returns:
        str: Standardized filename
    """
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*!@#$%^&(){}\[\]]', "_", filename)
    
    # Replace spaces and multiple underscores with single underscore
    filename = re.sub(r"[\s_]+", "_", filename)
    
    # Remove leading/trailing dots and underscores
    filename = filename.strip(". _")
    
    return filename


def get_parsed_output_path(input_path: Path, output_dir: Path, suffix: str = "") -> Path:
    """Get output path for parsed file.

    Args:
        input_path: Input file path
        output_dir: Output directory
        suffix: Optional suffix to add to filename

    Returns:
        Path: Output file path
    """
    # Get stem without extensions
    stem = input_path.stem
    while "." in stem:
        stem = stem.rsplit(".", 1)[0]
    
    # Standardize filename
    stem = standardize_filename(stem)
    
    # Add suffix if provided
    if suffix and not suffix.startswith("."):
        suffix = "." + suffix
    
    # Create output path
    output_path = output_dir / f"{stem}{suffix}.md"
    
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    return output_path


def preserve_relative_path(file_path: Path, base_dir: Path, output_dir: Path) -> Path:
    """Preserve relative path structure when copying files.

    Args:
        file_path: Path to file
        base_dir: Base directory
        output_dir: Output directory

    Returns:
        Path: Output path preserving relative structure
    """
    try:
        # Get relative path from base directory
        relative_path = file_path.relative_to(base_dir)
        
        # Create output path preserving structure
        output_path = output_dir / relative_path
        
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        return output_path
    
    except ValueError:
        # If file is not under base directory, use filename only
        logger.warning(f"File {file_path} is not under base directory {base_dir}")
        return output_dir / file_path.name
