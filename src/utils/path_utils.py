import os
from pathlib import Path
from typing import Union

from rich.text import Text


def format_path(path: Union[str, Path]) -> Text:
    """
    Format a path for display with consistent styling.

    Args:
        path: Path to format

    Returns:
        Text: Rich Text object with consistent path styling
    """
    path_str = str(path)
    normalized = path_str.replace(str(Path.home()), "~")
    return Text(normalized, style="path")


def normalize_path(path: Union[str, Path], for_display: bool = True) -> str:
    """Normalize path for display or system use."""
    path_str = str(path)
    normalized = path_str.replace(str(Path.home()), "~")
    return normalized


def get_file_size(path: Union[str, Path]) -> str:
    """Get human-readable file size."""
    size_bytes = Path(path).stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    return f"{size_mb:.1f}MB"


def ensure_directory(path: Union[str, Path]) -> None:
    """Create directory and any parent directories if they don't exist."""
    Path(path).mkdir(parents=True, exist_ok=True)


def ensure_dir_exists(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path to ensure exists

    Returns:
        Path object of the directory

    Raises:
        NotADirectoryError: If path exists but is not a directory
    """
    path = Path(path)
    if path.exists() and not path.is_dir():
        raise NotADirectoryError(f"Path exists but is not a directory: {path}")
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_relative_path(path: Union[str, Path], base_path: Union[str, Path]) -> Path:
    """
    Get the relative path from base_path to path.

    Args:
        path: Target path
        base_path: Base path to get relative path from

    Returns:
        Relative path from base_path to path
    """
    path = Path(path)
    base_path = Path(base_path)
    return path.relative_to(base_path)


def is_file_newer(file1: Union[str, Path], file2: Union[str, Path]) -> bool:
    """
    Check if file1 is newer than file2.

    Args:
        file1: First file to compare
        file2: Second file to compare

    Returns:
        True if file1 is newer than file2

    Raises:
        FileNotFoundError: If either file doesn't exist
    """
    file1, file2 = Path(file1), Path(file2)

    if not file1.exists():
        raise FileNotFoundError(f"File not found: {file1}")
    if not file2.exists():
        raise FileNotFoundError(f"File not found: {file2}")

    return file1.stat().st_mtime > file2.stat().st_mtime
