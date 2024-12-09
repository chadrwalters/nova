from pathlib import Path
from typing import Optional

from src.utils.colors import NovaConsole

from .path_utils import normalize_path

console = NovaConsole()


def print_status(message: str, path: Optional[str] = None) -> None:
    """Print status message with optional path.

    Args:
        message: The message to print
        path: Optional path to include in the message
    """
    if path:
        message = f"{message}: {normalize_path(path)}"
    console.info(message)


def print_success(message: str) -> None:
    """Print success message.

    Args:
        message: The success message to print
    """
    console.success(message)


def print_error(message: str) -> None:
    """Print error message.

    Args:
        message: The error message to print
    """
    console.error(message)
