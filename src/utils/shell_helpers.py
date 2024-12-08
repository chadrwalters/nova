from colors import NovaConsole

from .path_utils import normalize_path

console = NovaConsole()


def print_status(message: str, path: str = None) -> None:
    """Print status message with optional path."""
    if path:
        message = f"{message}: {normalize_path(path)}"
    console.info(message)


def print_success(message: str) -> None:
    """Print success message."""
    console.success(message)


def print_error(message: str) -> None:
    """Print error message."""
    console.error(message)
