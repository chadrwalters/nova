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
    normalized = path_str.replace(str(Path.home()), '~')
    return Text(normalized, style="path")

def normalize_path(path: Union[str, Path], for_display: bool = True) -> str:
    """Normalize path for display or system use."""
    path_str = str(path)
    normalized = path_str.replace(str(Path.home()), '~')
    return normalized

def get_file_size(path: Union[str, Path]) -> str:
    """Get human-readable file size."""
    size_bytes = Path(path).stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    return f"{size_mb:.1f}MB"

def ensure_directory(path: Union[str, Path]) -> None:
    """Create directory and any parent directories if they don't exist."""
    Path(path).mkdir(parents=True, exist_ok=True)
  