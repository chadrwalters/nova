"""Document converter class."""

import json
import logging
import os
from datetime import datetime, date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast, TypedDict, NotRequired, Union

import chardet
import frontmatter  # type: ignore
import pdfplumber
import pypandoc
from PIL import Image, ExifTags, UnidentifiedImageError
import pillow_heif
import piexif
import xml.etree.ElementTree as ET

from .datamodel.base_models import InputFormat, FORMAT_TO_MIME
from .datamodel.document import Document


class DocumentConversionError(Exception):
    """Exception raised when document conversion fails."""
    pass


logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)  # Set to WARNING to reduce noise


class ImageMetadata(TypedDict, total=False):
    """Type hints for image metadata."""
    format: str
    mode: str
    size: str
    exif: dict[str, str]
    frames: str


class SVGDimensions(TypedDict):
    """Type hints for SVG dimensions."""
    x: str
    y: str
    width: str
    height: str


class SVGMetadata(TypedDict):
    """Type hints for SVG metadata."""
    viewBox: NotRequired[str]
    dimensions: NotRequired[SVGDimensions]
    width: NotRequired[str]
    height: NotRequired[str]
    version: NotRequired[str]


def _normalize_path(file_path: Path, relative_to: Optional[Path] = None) -> str:
    """Normalize a file path.

    Args:
        file_path: The path to normalize.
        relative_to: Optional path to make the file_path relative to.

    Returns:
        Normalized path as a string, using forward slashes.
    """
    if relative_to is not None:
        try:
            # Make path relative if possible
            normalized = str(file_path.relative_to(relative_to))
        except ValueError:
            # If paths are on different drives or can't be made relative,
            # use absolute path
            normalized = str(file_path)
    else:
        normalized = str(file_path)

    # Convert backslashes to forward slashes for markdown compatibility
    return normalized.replace("\\", "/")


def _convert_image_to_markdown(image_path: Path, converter: 'DocumentConverter') -> Document:
    """Convert an image file to markdown format."""
    try:
        image = Image.open(image_path)
        metadata: dict[str, Union[str, date, datetime, list[str]]] = {
            "format": str(image.format).lower(),
            "mode": str(image.mode),
            "size": f"{image.width}x{image.height}",
        }

        # Extract format-specific metadata
        if image.format == "PNG":
            for key, value in image.info.items():
                if isinstance(value, (str, int, float, bool)):
                    metadata[f"png_{key}"] = str(value)
        elif image.format == "JPEG":
            try:
                exif_dict = piexif.load(image.info.get("exif", b""))
                for ifd in ("0th", "Exif", "GPS"):
                    if ifd in exif_dict:
                        for tag, value in exif_dict[ifd].items():
                            try:
                                if ifd == "0th":
                                    tag_name = piexif.TAGS["Image"][tag]["name"]
                                elif ifd == "Exif":
                                    tag_name = piexif.TAGS["Exif"][tag]["name"]
                                elif ifd == "GPS":
                                    tag_name = piexif.TAGS["GPS"][tag]["name"]
                                else:
                                    continue

                                if isinstance(value, bytes):
                                    try:
                                        value = value.decode('utf-8')
                                    except UnicodeDecodeError:
                                        value = value.hex()
                                metadata[f"exif_{tag_name}"] = str(value)
                            except KeyError:
                                continue
            except Exception as e:
                logger.warning(f"Error extracting EXIF data: {e}")
        elif image.format == "WEBP":
            # Properly handle WebP metadata
            is_lossless = image.info.get("lossless") is True or (image.mode == "RGB" and "transparency" not in image.info)
            metadata["webp_lossless"] = "True" if is_lossless else "False"
            metadata["webp_quality"] = "100" if is_lossless else str(image.info.get("quality", 0))
            if "loop" in image.info:
                metadata["webp_loop"] = str(image.info["loop"])
            if "duration" in image.info:
                metadata["webp_duration"] = str(image.info["duration"])

        # Generate markdown content
        content = [
            f"# {image.format}: {image_path.name}",
            "",
            "## Image Information",
            "",
            f"- Format: {metadata['format']}",
            f"- Mode: {metadata['mode']}",
            f"- Size: {metadata['size']}",
        ]

        # Use _detect_format to get the correct format
        fmt = converter._detect_format(image_path)

        return Document(
            content="\n".join(content),
            format=fmt,
            metadata=metadata,
            source_path=image_path,
        )
    except Exception as e:
        raise DocumentConversionError(f"Error converting image file {image_path}: {e}")


def _convert_svg_to_markdown(file_path: Path) -> Document:
    """Convert SVG file to markdown.

    Args:
        file_path: Path to SVG file.

    Returns:
        Document: The converted document.

    Raises:
        DocumentConversionError: If conversion fails.
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Extract metadata
        metadata: dict[str, Union[str, date, datetime, list[str]]] = {
            "format": "svg",
            "xmlns": root.get("xmlns", "http://www.w3.org/2000/svg"),
            "width": root.get("width", ""),
            "height": root.get("height", ""),
            "viewBox": root.get("viewBox", ""),
            "version": root.get("version", "1.1"),
        }

        # Extract title and description if present
        title_elem = root.find("{http://www.w3.org/2000/svg}title")
        if title_elem is not None and title_elem.text:
            metadata["title"] = title_elem.text

        desc_elem = root.find("{http://www.w3.org/2000/svg}desc")
        if desc_elem is not None and desc_elem.text:
            metadata["description"] = desc_elem.text

        # Count SVG elements
        element_counts: dict[str, int] = {}
        for elem in root.iter():
            tag = elem.tag.split('}')[-1]  # Remove namespace
            element_counts[tag] = element_counts.get(tag, 0) + 1
        metadata["element_counts"] = json.dumps(element_counts)

        # Generate markdown content
        content = f"![{metadata.get('title', file_path.stem)}]({file_path})"

        return Document(
            content=content,
            format=InputFormat.SVG,
            metadata=cast(dict[str, Union[str, date, datetime, list[str]]], metadata),
            source_path=file_path
        )
    except Exception as e:
        raise DocumentConversionError(f"Error converting SVG file {file_path}: {str(e)}")


def _convert_metadata(raw_metadata: dict[str, Any]) -> dict[str, Union[str, date, datetime, list[str]]]:
    """Convert metadata values to strings.

    Args:
        raw_metadata: Raw metadata dictionary.

    Returns:
        Dictionary with all values converted to strings.
    """
    result: dict[str, Union[str, date, datetime, list[str]]] = {}
    for key, value in raw_metadata.items():
        if isinstance(value, (date, datetime)):
            result[str(key)] = value
        elif isinstance(value, (list, tuple)):
            # Special handling for tags - keep as list
            if key == "tags":
                result[str(key)] = [str(v) for v in value]
            else:
                result[str(key)] = ", ".join(str(v) for v in value)
        elif isinstance(value, dict):
            # Flatten nested dictionaries with dot notation
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, (date, datetime)):
                    result[f"{key}.{sub_key}"] = sub_value
                else:
                    result[f"{key}.{sub_key}"] = str(sub_value)
        else:
            result[str(key)] = str(value)
    return result


class MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.metadata: dict[str, str] = {}
        self.in_title = False
        self.current_meta = None

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            attrs_dict = dict((k, v) for k, v in attrs if v is not None)
            name = attrs_dict.get("name", "")
            content = attrs_dict.get("content", "")

            # Handle common metadata
            if name in ["author", "description", "keywords", "date", "language", "copyright"]:
                self.metadata[name] = content
            # Handle Open Graph metadata
            elif name.startswith("og:"):
                self.metadata[name[3:]] = content
            # Handle Dublin Core metadata
            elif name.startswith("dc."):
                self.metadata[name[3:]] = content

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.metadata["title"] = data.strip()


class DocumentConverter:
    """Document converter class."""

    def __init__(self) -> None:
        """Initialize the document converter."""
        self.supported_formats = {
            InputFormat.MD,
            InputFormat.HTML,
            InputFormat.PDF,
            InputFormat.TEXT,
            InputFormat.PNG,
            InputFormat.JPEG,
            InputFormat.GIF,
            InputFormat.WEBP,
            InputFormat.SVG,
            InputFormat.HEIC,
            InputFormat.JSON,
        }

    def _detect_format(self, file_path: Path) -> InputFormat:
        """Detect the format of a file based on its extension.

        Args:
            file_path: Path to the file.

        Returns:
            Detected input format.
        """
        ext = file_path.suffix.lower()
        if ext == ".md":
            return InputFormat.MD
        elif ext == ".html":
            return InputFormat.HTML
        elif ext == ".pdf":
            return InputFormat.PDF
        elif ext == ".txt":
            return InputFormat.TEXT
        elif ext == ".png":
            return InputFormat.PNG
        elif ext in [".jpg", ".jpeg"]:  # Handle both jpg and jpeg
            return InputFormat.JPEG
        elif ext == ".gif":
            return InputFormat.GIF
        elif ext == ".webp":
            return InputFormat.WEBP
        elif ext == ".svg":
            return InputFormat.SVG
        elif ext == ".heic":
            return InputFormat.HEIC
        elif ext == ".json":
            return InputFormat.JSON
        else:
            return InputFormat.TEXT  # Default to text for unknown extensions

    def convert(self, file_path: Path, fmt: Optional[InputFormat] = None) -> Document:
        """Convert a file to markdown format.

        Args:
            file_path: Path to the file to convert
            fmt: Optional format override. If not provided, will be detected from file extension.

        Returns:
            Document object containing the markdown content and metadata

        Raises:
            DocumentConversionError: If conversion fails
        """
        try:
            if fmt is None:
                fmt = self._detect_format(file_path)

            if fmt not in self.supported_formats:
                raise DocumentConversionError(f"Unsupported format: {fmt}")

            if fmt == InputFormat.HEIC:
                return _convert_heic_to_markdown(file_path)
            elif fmt in [InputFormat.PNG, InputFormat.JPEG, InputFormat.GIF, InputFormat.WEBP]:
                return _convert_image_to_markdown(file_path, self)
            elif fmt == InputFormat.MD:
                return _convert_markdown_to_markdown(file_path)
            elif fmt == InputFormat.HTML:
                return _convert_html_to_markdown(file_path)
            elif fmt == InputFormat.JSON:
                return _convert_json_to_markdown(file_path)
            elif fmt == InputFormat.SVG:
                return _convert_svg_to_markdown(file_path)
            elif fmt == InputFormat.TEXT:
                return _convert_text_to_markdown(file_path)
            elif fmt == InputFormat.PDF:
                return _convert_pdf_to_markdown(file_path)
            else:
                raise DocumentConversionError(f"Unsupported format: {fmt}")
        except Exception as e:
            raise DocumentConversionError(f"Error converting file {file_path}: {e}")


def _convert_markdown_to_markdown(file_path: Path) -> Document:
    """Convert markdown file to Document.

    This is mostly a pass-through that extracts frontmatter metadata.

    Args:
        file_path: Path to markdown file

    Returns:
        Document with content and metadata

    Raises:
        DocumentConversionError: If conversion fails
    """
    try:
        # Parse frontmatter and content
        with open(file_path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)

        # Extract metadata
        metadata = _convert_metadata(post.metadata)

        return Document(
            content=post.content,
            format=InputFormat.MD,
            metadata=metadata,
            source_path=file_path
        )
    except Exception as e:
        raise DocumentConversionError(f"Error converting markdown file {file_path}: {e}")


def _convert_json_to_markdown(file_path: Path) -> Document:
    """Convert JSON file to Document.

    Args:
        file_path: Path to JSON file

    Returns:
        Document with content and metadata

    Raises:
        DocumentConversionError: If conversion fails
    """
    try:
        # Read and parse JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Format as markdown
        content = json.dumps(data, indent=2)

        # Extract metadata
        metadata: dict[str, Union[str, date, datetime, list[str]]] = {
            "format": "json",
            "size": str(file_path.stat().st_size),
            "modified": datetime.fromtimestamp(file_path.stat().st_mtime_ns / 1e9)
        }

        return Document(
            content=content,
            format=InputFormat.JSON,
            metadata=metadata,
            source_path=file_path
        )
    except Exception as e:
        raise DocumentConversionError(f"Error converting JSON file {file_path}: {e}")


def _convert_html_to_markdown(file_path: Path) -> Document:
    """Convert HTML file to markdown format.

    Args:
        file_path: Path to the HTML file.

    Returns:
        Document object containing markdown content and metadata.

    Raises:
        DocumentConversionError: If conversion fails.
    """
    try:
        # Parse metadata first
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        parser = MetadataParser()
        parser.feed(html_content)
        metadata: dict[str, Union[str, date, datetime, list[str]]] = {
            k: v for k, v in parser.metadata.items()
        }

        # Convert HTML to markdown using pandoc
        output = pypandoc.convert_file(
            str(file_path),
            'markdown',
            format='html'
        )

        return Document(
            content=output,
            format=InputFormat.HTML,
            metadata=metadata,
            source_path=file_path
        )
    except Exception as e:
        raise DocumentConversionError(f"Error converting HTML file {file_path}: {e}")


def _convert_text_to_markdown(file_path: Path) -> Document:
    """Convert text file to markdown format.

    Args:
        file_path: Path to the text file.

    Returns:
        Document object containing markdown content and metadata.

    Raises:
        DocumentConversionError: If conversion fails.
    """
    try:
        # Detect encoding
        with open(file_path, 'rb') as f:
            raw = f.read()
            result = chardet.detect(raw)
            encoding = result['encoding'] or 'utf-8'

        # Read file with detected encoding
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()

        # Extract basic metadata
        metadata: dict[str, Union[str, date, datetime, list[str]]] = {
            "format": "text",
            "encoding": encoding,
            "size": str(len(content)),
            "lines": str(len(content.splitlines())),
        }

        return Document(
            content=content,
            format=InputFormat.TEXT,
            metadata=metadata,
            source_path=file_path
        )
    except Exception as e:
        raise DocumentConversionError(f"Error converting text file {file_path}: {e}")


def _convert_pdf_to_markdown(file_path: Path) -> Document:
    """Convert PDF file to markdown format.

    Args:
        file_path: Path to the PDF file.

    Returns:
        Document object containing markdown content and metadata.

    Raises:
        DocumentConversionError: If conversion fails.
    """
    try:
        # Extract text and metadata using pdfplumber
        with pdfplumber.open(file_path) as pdf:
            # Extract metadata
            metadata: dict[str, Union[str, date, datetime, list[str]]] = {
                "format": "pdf",
                "pages": str(len(pdf.pages)),
                "size": str(file_path.stat().st_size),
            }

            # Add PDF metadata if available
            if pdf.metadata:
                for key, value in pdf.metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        metadata[f"pdf_{key}"] = str(value)

            # Extract text from each page
            content = []
            for i, page in enumerate(pdf.pages, 1):
                # Add page header
                content.append(f"\n## Page {i}\n")

                # Extract text
                text = page.extract_text()
                if text:
                    content.append(text)

                # Add page metadata
                page_dims = page.width, page.height
                metadata[f"page_{i}_dimensions"] = f"{page_dims[0]:.2f}x{page_dims[1]:.2f}"

        return Document(
            content="\n".join(content),
            format=InputFormat.PDF,
            metadata=metadata,
            source_path=file_path
        )
    except Exception as e:
        raise DocumentConversionError(f"Error converting PDF file {file_path}: {e}")


def _convert_heic_to_markdown(file_path: Path) -> Document:
    """Convert HEIC image to markdown.

    Args:
        file_path: Path to HEIC file.

    Returns:
        Document object containing markdown content and metadata.

    Raises:
        DocumentConversionError: If conversion fails.
    """
    try:
        # Read HEIC file
        heif_file = pillow_heif.read_heif(str(file_path))
        data = heif_file.data
        if data is None:
            raise ValueError("Failed to read HEIC data")

        image = Image.frombytes(
            heif_file.mode,
            heif_file.size,
            data,
            "raw",
            heif_file.mode,
            heif_file.stride,
        )

        # Extract metadata
        metadata: dict[str, Union[str, date, datetime, list[str]]] = {
            "format": "heic",
            "mode": str(image.mode),
            "size": f"{image.width}x{image.height}",
        }

        # Extract EXIF data if available
        try:
            exif_data = image.getexif()
            if exif_data:
                exif_dict: dict[str, str] = {}
                for tag_id in exif_data:
                    # Get the tag name, default to the tag ID if not known
                    tag = ExifTags.TAGS.get(tag_id, str(tag_id))
                    value = exif_data.get(tag_id)
                    if value is not None:
                        exif_dict[str(tag)] = str(value)
                metadata["exif"] = json.dumps(exif_dict)
        except Exception as e:
            logger.warning(f"Error extracting EXIF data: {e}")

        # Generate markdown content
        content = f"# HEIC: {file_path.name}\n\n"
        content += "## Image Information\n\n"
        content += f"- Format: {metadata['format']}\n"
        content += f"- Mode: {metadata['mode']}\n"
        content += f"- Size: {metadata['size']}\n"

        return Document(
            content=content,
            format=InputFormat.HEIC,
            metadata=metadata,
            source_path=file_path
        )
    except Exception as e:
        raise DocumentConversionError(f"Error converting HEIC file {file_path}: {e}")
