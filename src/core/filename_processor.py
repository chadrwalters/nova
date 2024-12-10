import re
import unicodedata
from pathlib import Path
from typing import Optional

from src.core.logging import get_logger

logger = get_logger(__name__)


class FilenameProcessor:
    """Processes filenames to ensure they are valid and consistent."""

    def __init__(self):
        # Initialize patterns
        self.invalid_chars = re.compile(r'[<>:"/\\|?*\x00-\x1F]')
        self.spaces = re.compile(r"\s+")
        self.dots = re.compile(r"\.+")
        self.dashes = re.compile(r"-+")
        self.underscores = re.compile(r"_+")
        self.leading_trailing = re.compile(r"^[-._\s]+|[-._\s]+$")

    def clean_filename(
        self, filename: str, max_length: int = 255, replacement: str = "-"
    ) -> str:
        """Clean a filename to make it safe and consistent."""
        try:
            # Normalize unicode characters
            filename = unicodedata.normalize("NFKD", filename)
            filename = "".join(c for c in filename if not unicodedata.combining(c))

            # Replace invalid characters
            filename = self.invalid_chars.sub(replacement, filename)

            # Replace spaces
            filename = self.spaces.sub(replacement, filename)

            # Replace multiple dots
            filename = self.dots.sub(".", filename)

            # Replace multiple dashes
            filename = self.dashes.sub(replacement, filename)

            # Replace multiple underscores
            filename = self.underscores.sub("_", filename)

            # Remove leading/trailing separators
            filename = self.leading_trailing.sub("", filename)

            # Ensure filename is not empty
            if not filename:
                return "unnamed"

            # Truncate if too long
            name_parts = filename.rsplit(".", 1)
            if len(name_parts) > 1:
                name, ext = name_parts
                # Reserve space for extension
                max_name_length = max_length - len(ext) - 1
                if len(name) > max_name_length:
                    name = name[:max_name_length]
                filename = f"{name}.{ext}"
            else:
                if len(filename) > max_length:
                    filename = filename[:max_length]

            return filename

        except Exception as e:
            logger.error("Filename cleaning failed", error=str(e), filename=filename)
            return "unnamed"

    def make_unique(
        self, base_path: Path, filename: str, max_attempts: int = 1000
    ) -> Optional[str]:
        """Make a filename unique in the given directory."""
        try:
            # Clean filename first
            filename = self.clean_filename(filename)

            # Split name and extension
            name_parts = filename.rsplit(".", 1)
            if len(name_parts) > 1:
                name, ext = name_parts
                ext = f".{ext}"
            else:
                name = filename
                ext = ""

            # Try original name first
            if not (base_path / filename).exists():
                return filename

            # Try adding numbers
            for i in range(1, max_attempts):
                new_name = f"{name}_{i}{ext}"
                if not (base_path / new_name).exists():
                    return new_name

            # If we get here, we've run out of attempts
            logger.error(
                "Failed to create unique filename",
                filename=filename,
                attempts=max_attempts,
            )
            return None

        except Exception as e:
            logger.error(
                "Unique filename generation failed", error=str(e), filename=filename
            )
            return None

    def get_safe_path(
        self, base_path: Path, relative_path: str, create_dirs: bool = True
    ) -> Optional[Path]:
        """Get a safe path relative to the base path."""
        try:
            # Clean path components
            parts = [self.clean_filename(part) for part in Path(relative_path).parts]

            # Combine parts
            clean_path = Path(*parts)

            # Ensure path is relative
            if clean_path.is_absolute():
                clean_path = Path(*clean_path.parts[1:])

            # Combine with base path
            full_path = base_path / clean_path

            # Create parent directories if needed
            if create_dirs:
                full_path.parent.mkdir(parents=True, exist_ok=True)

            return full_path

        except Exception as e:
            logger.error(
                "Safe path generation failed",
                error=str(e),
                base=str(base_path),
                path=relative_path,
            )
            return None

    def is_safe_path(self, base_path: Path, check_path: Path) -> bool:
        """Check if a path is safe (no directory traversal)."""
        try:
            # Resolve paths
            base_abs = base_path.resolve()
            check_abs = check_path.resolve()

            # Check if path is under base directory
            return str(check_abs).startswith(str(base_abs))

        except Exception as e:
            logger.error(
                "Path safety check failed",
                error=str(e),
                base=str(base_path),
                path=str(check_path),
            )
            return False


__all__ = ["FilenameProcessor"]
