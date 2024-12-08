#!/usr/bin/env python3

"""Markdown file consolidation module."""

import base64
import hashlib
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import typer
from PIL import Image

from src.utils.colors import NovaConsole
from src.utils.timing import timed_section

app = typer.Typer(help="Nova Markdown Consolidator")
nova_console = NovaConsole()


@dataclass
class MarkdownFile:
    """Represents a processed markdown file with its metadata."""

    path: Path
    date: datetime
    content: str
    media_files: List[Path]


def extract_date_from_filename(filename: str) -> datetime:
    """Extract date from filename in format YYYYMMDD."""
    match = re.match(r"(\d{8})", filename)
    if match:
        date_str = match.group(1)
        try:
            return datetime.strptime(date_str, "%Y%m%d")
        except ValueError:
            pass
    return datetime.fromtimestamp(0)  # Default to epoch if no date found


def process_base64_image(
    alt_text: str, image_type: str, base64_data: str, file_path: Path, media_dir: Path
) -> Tuple[str, Optional[Path]]:
    """Process a base64 encoded image and save it to the media directory."""
    try:
        # Ensure media directory exists
        media_dir.mkdir(parents=True, exist_ok=True)

        content_hash = hashlib.md5(base64_data.encode()).hexdigest()[:12]
        image_filename = f"{file_path.stem}_{content_hash}.{image_type}"
        image_path = media_dir / image_filename

        if not image_path.exists():
            image_data = base64.b64decode(base64_data)
            image_path.write_bytes(image_data)

        return f"![{alt_text}](_media/{image_filename})", image_path

    except Exception as err:
        nova_console.error(f"Failed to process base64 image: {err}")
        return f"![{alt_text}](error_processing_image)", None


def get_search_paths(file_path: Path, image_name: str) -> List[Path]:
    """Generate list of possible image paths to search."""
    clean_name = Path(image_name).name
    number_pattern = re.sub(r"^(\d+).*$", r"\1", clean_name)

    paths = [
        file_path.parent / image_name,  # Direct path
        file_path.parent / clean_name,  # Clean name in same dir
        file_path.parent / "_media" / clean_name,  # Clean name in _media
    ]

    # Add paths with different extensions
    for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".svg"]:
        paths.extend(
            [
                file_path.parent / f"{number_pattern}{ext}",
                file_path.parent / "_media" / f"{number_pattern}{ext}",
            ]
        )

    return paths


def convert_heic_to_png(
    source_path: Path, target_path: Path, alt_text: str, image_path: str
) -> Tuple[str, Optional[Path]]:
    """Convert HEIC image to PNG format."""
    try:
        import pillow_heif

        heif_file = pillow_heif.read_heif(str(source_path))
        image = Image.frombytes(
            heif_file.mode,
            heif_file.size,
            heif_file.data,
            "raw",
            heif_file.mode,
            heif_file.stride,
        )
        image.save(target_path, "PNG")
        nova_console.process_item(
            f"Converted and copied image: {source_path} -> {target_path}"
        )
        return f"![{alt_text}](_media/{target_path.name})", target_path
    except Exception as err:
        nova_console.warning(f"Failed to convert HEIC image {source_path}: {err}")
        try:
            # Try using PIL's built-in HEIC support as fallback
            image = Image.open(source_path)
            image.save(target_path, "PNG")
            nova_console.process_item(
                f"Converted and copied image using PIL: {source_path} -> {target_path}"
            )
            return f"![{alt_text}](_media/{target_path.name})", target_path
        except Exception as err2:
            nova_console.error(
                f"Failed to convert HEIC image using PIL {source_path}: {err2}"
            )
            return f"![{alt_text}]({image_path})", None


def copy_image_file(
    source_path: Path, target_path: Path, alt_text: str
) -> Tuple[str, Path]:
    """Copy image file to target location."""
    if not target_path.exists():
        shutil.copy2(source_path, target_path)
        nova_console.process_item(f"Copied image: {source_path} -> {target_path}")
    return f"![{alt_text}](_media/{target_path.name})", target_path


def find_similar_image(
    search_paths: List[Path],
    image_name: str,
    file_path: Path,
    media_dir: Path,
    alt_text: str,
) -> Tuple[str, Optional[Path]]:
    """Find and process similar image files."""
    similar_files = []
    for path in search_paths:
        if path.parent.exists():
            for file in path.parent.glob("*"):
                is_image = file.name.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".svg")
                )
                if is_image and image_name.lower() in file.name.lower():
                    similar_files.append(file)

    if similar_files:
        source_path = similar_files[0]
        nova_console.process_item(f"Found similar image: {source_path}")

        new_filename = source_path.name
        if (media_dir / new_filename).exists():
            new_filename = f"{file_path.stem}_{new_filename}"

        target_path = media_dir / new_filename
        return copy_image_file(source_path, target_path, alt_text)

    nova_console.warning(f"Image not found for {file_path.name}: {image_name}")
    return f"![{alt_text}]({image_name})", None


def process_local_image(
    match: re.Match, file_path: Path, media_dir: Path
) -> Tuple[str, Optional[Path]]:
    """Process a local image reference in markdown."""
    alt_text = match.group(1)
    image_path = match.group(2)

    try:
        # Skip if the image is already in the media directory
        if image_path.startswith("_media/"):
            return f"![{alt_text}]({image_path})", None

        # Remove any _media/ prefix from the search
        clean_image_path = image_path.replace("_media/", "")
        image_name = Path(clean_image_path).name

        # Get all possible search paths
        search_paths = get_search_paths(file_path, clean_image_path)

        # Try each path until we find the image
        for path in search_paths:
            if path.exists():
                nova_console.process_item(f"Found image at: {path}")

                # Create new filename with markdown file name as prefix
                new_filename = f"{file_path.stem}_{path.name}"
                target_path = media_dir / new_filename

                # Handle HEIC/HEIF images
                if path.suffix.lower() in [".heic", ".heif"]:
                    return convert_heic_to_png(path, target_path, alt_text, image_path)

                # Handle other image formats
                return copy_image_file(path, target_path, alt_text)

        # If no exact match found, try similar files
        return find_similar_image(
            search_paths, image_name, file_path, media_dir, alt_text
        )

    except Exception as err:
        nova_console.warning(f"Failed to process image {image_path}: {err}")
        return f"![{alt_text}]({image_path})", None


def process_image_links(
    content: str, file_path: Path, media_dir: Path
) -> Tuple[str, List[Path]]:
    """Process and extract image links from markdown content."""
    media_files: List[Path] = []

    def handle_base64_match(match: re.Match) -> str:
        """Handle base64 image match and update media_files."""
        markdown_text, image_path = process_base64_image(
            match.group(1),  # alt_text
            match.group(2),  # image_type
            match.group(3),  # base64_data
            file_path,
            media_dir,
        )
        if image_path:
            media_files.append(image_path)
        return markdown_text

    def handle_local_image_match(match: re.Match) -> str:
        """Handle local image match and update media_files."""
        markdown_text, image_path = process_local_image(match, file_path, media_dir)
        if image_path:
            media_files.append(image_path)
        return markdown_text

    # Process base64 encoded images first
    content = re.sub(
        r"!\[([^\]]*)\]\(data:image/([^;]+);base64,([^\)]+)\)",
        handle_base64_match,
        content,
    )

    # Then process local image references (excluding base64 images)
    content = re.sub(
        r"!\[([^\]]*)\]\((?!data:image/)([^:\)]+)\)", handle_local_image_match, content
    )

    return content, media_files


def process_file(file_path: Path, media_dir: Path) -> MarkdownFile:
    """Process a single markdown file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        date = extract_date_from_filename(file_path.stem)
        processed_content, media_files = process_image_links(
            content, file_path, media_dir
        )
        return MarkdownFile(
            path=file_path,
            date=date,
            content=processed_content,
            media_files=media_files,
        )
    except Exception as err:
        nova_console.error(f"Failed to process file {file_path}")
        raise err from err


def consolidate(
    input_dir: Path,
    output_file: Path,
    *,
    recursive: bool = False,
    verbose: bool = False,
) -> None:
    """Consolidate markdown files from input directory into a single file."""
    try:
        if not input_dir.is_dir():
            msg = f"Input directory does not exist: {input_dir}"
            raise FileNotFoundError(msg)
        pattern = "**/*.md" if recursive else "*.md"
        markdown_files = sorted(
            input_dir.glob(pattern),
            key=lambda x: (extract_date_from_filename(x.stem), x.name),
        )
        if not markdown_files:
            msg = f"No markdown files found in {input_dir}"
            raise FileNotFoundError(msg)
        processed_files = []
        for file_path in markdown_files:
            if verbose:
                nova_console.process_item(f"Processing {file_path}")
            try:
                processed_file = process_file(file_path, output_file.parent / "_media")
                processed_files.append(processed_file)
            except Exception as err:
                nova_console.error(f"Failed to process {file_path}: {err}")
                continue
        processed_files.sort(key=lambda x: (x.date, x.path.name))
        consolidated_content = "\n\n".join(f.content for f in processed_files)
        output_file.write_text(consolidated_content, encoding="utf-8")
    except Exception as err:
        nova_console.error("Failed to consolidate markdown files")
        raise err from err


if __name__ == "__main__":
    app()
