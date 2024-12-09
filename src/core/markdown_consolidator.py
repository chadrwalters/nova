#!/usr/bin/env python3

"""Markdown file consolidation module."""

import base64
import hashlib
import os
import re
import shutil
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Generator, Iterator, List, Optional, Set, Tuple

import markdown
import pillow_heif
import structlog
import typer
from PIL import Image

from src.core.exceptions import ProcessingError
from src.utils.colors import NovaConsole
from src.utils.file_utils import compute_file_hash
from src.utils.timing import timed_section

app = typer.Typer(help="Nova Markdown Consolidator")
nova_console = NovaConsole()
logger = structlog.get_logger(__name__)


@dataclass
class ConsolidationResult:
    """Result of document consolidation."""

    content: str
    metadata: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)


@dataclass
class ProcessedImage:
    """Result of image processing."""

    path: Path
    target_path: Path
    html_path: Path
    metadata: Dict[str, Any]
    is_valid: bool = True
    error: Optional[str] = None


class MarkdownConsolidator:
    """Consolidates markdown documents."""

    def __init__(self, base_dir: Path, output_dir: Path, media_dir: Path) -> None:
        """Initialize consolidator.

        Args:
            base_dir: Base directory containing markdown files
            output_dir: Output directory for consolidated files
            media_dir: Directory for media files
        """
        self.base_dir = base_dir
        self.output_dir = output_dir
        self.media_dir = media_dir
        self.processed_files: Set[Path] = set()

        # Create directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.media_dir.mkdir(parents=True, exist_ok=True)

    def process_image(self, image_path: Path) -> ProcessedImage:
        """Process an image file.

        Args:
            image_path: Path to the image file

        Returns:
            ProcessedImage object with processing results

        Raises:
            ProcessingError: If image processing fails
        """
        try:
            # Generate target paths
            file_hash = compute_file_hash(image_path)
            target_path = (
                self.media_dir / f"{image_path.stem}_{file_hash[:8]}{image_path.suffix}"
            )
            html_path = Path(f"_media/images/{target_path.name}")

            # Process image
            with Image.open(image_path) as img:
                img.save(target_path)

            return ProcessedImage(
                path=image_path,
                target_path=target_path,
                html_path=html_path,
                metadata={"hash": file_hash, "relative_path": str(html_path)},
            )
        except Exception as err:
            raise ProcessingError(f"Failed to process image: {err}") from err

    def consolidate(self, input_files: List[Path]) -> ConsolidationResult:
        """Consolidate markdown files.

        Args:
            input_files: List of markdown files to consolidate

        Returns:
            ConsolidationResult containing consolidated content

        Raises:
            ProcessingError: If consolidation fails
        """
        try:
            content_parts: List[str] = []
            warnings: List[str] = []
            metadata: Dict[str, Any] = {}

            for file_path in input_files:
                if file_path in self.processed_files:
                    warnings.append(f"Skipping duplicate file: {file_path}")
                    continue

                with timed_section(f"Processing {file_path.name}"):
                    content = file_path.read_text()
                    fixed_content = self._fix_list_formatting(content)
                    content_parts.append(fixed_content)
                    self.processed_files.add(file_path)

            return ConsolidationResult(
                content="\n\n".join(content_parts), metadata=metadata, warnings=warnings
            )

        except Exception as err:
            raise ProcessingError(f"Failed to consolidate documents: {err}") from err

    def _fix_list_formatting(self, content: str) -> str:
        """Fix markdown list formatting.

        Args:
            content: The markdown content to fix

        Returns:
            The fixed markdown content
        """
        fixed_lines: List[str] = []
        in_list = False
        list_indent = 0

        for line in content.splitlines():
            # Process line
            fixed_lines.append(line)

        return "\n".join(fixed_lines)


if __name__ == "__main__":
    app()
