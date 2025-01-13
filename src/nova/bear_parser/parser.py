"""Bear note parser implementation."""

import hashlib
import logging
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote

import pandas as pd
from docling.datamodel.base_models import (
    FormatToExtensions,
    FormatToMimeType,
    InputFormat,
)
from docling_core.types.doc.document import (
    DoclingDocument,
    DocumentOrigin,
    FloatingItem,
    ImageRef,
    PictureItem,
    TableCell,
    TableData,
    TableItem,
    TextItem,
)
from docling_core.types.doc.labels import DocItemLabel
from PIL import Image, UnidentifiedImageError
from pydantic import AnyUrl, parse_obj_as

logger = logging.getLogger(__name__)


class AttachmentError(Exception):
    """Error processing an attachment."""

    pass


class UnsupportedFormatError(Exception):
    """Unsupported file format."""

    pass


class BearParser:
    """Parser for Bear notes."""

    # Supported MIME types for attachments
    SUPPORTED_IMAGE_TYPES = {
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/tiff",
        "image/webp",
    }
    SUPPORTED_TABLE_TYPES = {"text/csv"}
    SUPPORTED_MIME_TYPES = SUPPORTED_IMAGE_TYPES | SUPPORTED_TABLE_TYPES

    # Size limits in bytes
    MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_TABLE_SIZE = 10 * 1024 * 1024  # 10MB

    # Image dimension limits
    MAX_IMAGE_WIDTH = 10000  # pixels
    MAX_IMAGE_HEIGHT = 10000  # pixels

    # Table dimension limits
    MAX_TABLE_ROWS = 1000000  # 1M rows
    MAX_TABLE_COLS = 1000  # 1K columns

    def __init__(self, input_dir: Path):
        """Initialize parser.

        Args:
            input_dir: Input directory containing Bear notes
        """
        self.input_dir = input_dir

    def _get_file_metadata(self, file_path: Path) -> dict[str, str]:
        """Get metadata for a file.

        Args:
            file_path: Path to file

        Returns:
            Dictionary containing file metadata
        """
        stat = file_path.stat()
        return {
            "filename": file_path.name,
            "original_path": str(file_path.absolute()),
            "relative_path": str(file_path.relative_to(self.input_dir)),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "size": str(stat.st_size),
        }

    def _validate_mime_type(self, file_path: Path) -> str:
        """Validate and return the MIME type of a file."""
        mime_type = mimetypes.guess_type(file_path)[0]
        if not mime_type:
            raise UnsupportedFormatError(
                f"Could not determine MIME type for {file_path}"
            )

        if mime_type.startswith("image/"):
            if mime_type not in self.SUPPORTED_IMAGE_TYPES:
                raise UnsupportedFormatError(f"Unsupported image format: {mime_type}")
        elif mime_type == "text/csv":
            pass  # CSV is the only supported table format
        else:
            raise UnsupportedFormatError(f"Unsupported file format: {mime_type}")

        return mime_type

    def _validate_file_size(self, file_path: Path, mime_type: str) -> None:
        """Validate size of a file.

        Args:
            file_path: Path to file
            mime_type: MIME type of file

        Raises:
            AttachmentError: If file size exceeds limit
        """
        size = file_path.stat().st_size

        if mime_type in self.SUPPORTED_IMAGE_TYPES:
            if size > self.MAX_IMAGE_SIZE:
                raise AttachmentError(
                    f"Image {file_path} size ({size} bytes) exceeds limit "
                    f"of {self.MAX_IMAGE_SIZE} bytes"
                )
        elif mime_type in self.SUPPORTED_TABLE_TYPES:
            if size > self.MAX_TABLE_SIZE:
                raise AttachmentError(
                    f"Table {file_path} size ({size} bytes) exceeds limit "
                    f"of {self.MAX_TABLE_SIZE} bytes"
                )

    def _validate_image(self, file_path: Path) -> Image.Image:
        """Validate an image file.

        Args:
            file_path: Path to image file

        Returns:
            Opened PIL Image

        Raises:
            AttachmentError: If image is invalid or exceeds limits
        """
        try:
            img = Image.open(file_path)
            if img.width > self.MAX_IMAGE_WIDTH or img.height > self.MAX_IMAGE_HEIGHT:
                raise AttachmentError(
                    f"Image {file_path} dimensions ({img.width}x{img.height}) exceed "
                    f"limits ({self.MAX_IMAGE_WIDTH}x{self.MAX_IMAGE_HEIGHT})"
                )
            return img
        except UnidentifiedImageError:
            raise AttachmentError(f"Invalid or corrupted image file: {file_path}")
        except Exception as e:
            raise AttachmentError(f"Failed to process image {file_path}: {e}")

    def _validate_table(self, file_path: Path) -> pd.DataFrame:
        """Validate a table file.

        Args:
            file_path: Path to table file

        Returns:
            Loaded pandas DataFrame

        Raises:
            AttachmentError: If table is invalid or exceeds limits
        """
        try:
            df = pd.read_csv(file_path)
            if len(df) > self.MAX_TABLE_ROWS:
                raise AttachmentError(
                    f"Table {file_path} has too many rows ({len(df)}). "
                    f"Maximum allowed: {self.MAX_TABLE_ROWS}"
                )
            if len(df.columns) > self.MAX_TABLE_COLS:
                raise AttachmentError(
                    f"Table {file_path} has too many columns ({len(df.columns)}). "
                    f"Maximum allowed: {self.MAX_TABLE_COLS}"
                )
            return df
        except pd.errors.EmptyDataError:
            raise AttachmentError(f"Empty table file: {file_path}")
        except pd.errors.ParserError:
            raise AttachmentError(f"Invalid CSV format in file: {file_path}")
        except Exception as e:
            raise AttachmentError(f"Failed to process table {file_path}: {e}")

    def _detect_format(self, file_path: Path) -> InputFormat:
        """Detect format of a file.

        Args:
            file_path: Path to file

        Returns:
            Detected format

        Raises:
            UnsupportedFormatError: If format is not supported
        """
        ext = file_path.suffix.lower()
        mime_type = mimetypes.guess_type(str(file_path))[0]

        # Check known extensions
        for fmt, exts in FormatToExtensions.items():
            if ext in exts:
                return fmt

        # Check mime types
        for fmt, types in FormatToMimeType.items():
            if mime_type in types:
                return fmt

        raise UnsupportedFormatError(f"Unsupported file format: {file_path}")

    def _make_file_uri(self, path: Path) -> AnyUrl:
        """Create a file URI from a path."""
        uri_str = f"file://localhost{quote(str(path.absolute()))}"
        return parse_obj_as(AnyUrl, uri_str)

    def _process_attachment(self, attachment_path: Path) -> FloatingItem | None:
        """Process an attachment file and return a FloatingItem."""
        try:
            # Validate format and size
            mime_type = self._validate_mime_type(attachment_path)
            self._validate_file_size(attachment_path, mime_type)

            # Process based on type
            if mime_type.startswith("image/"):
                self._validate_image(attachment_path)
                with Image.open(attachment_path) as img:
                    # Create picture item
                    item = PictureItem(
                        label=DocItemLabel.PICTURE,
                        self_ref=f"#/pictures/{attachment_path.name}",
                        captions=[],  # Bear notes don't support captions yet
                        references=[],  # No references in Bear notes
                        footnotes=[],  # No footnotes in Bear notes
                        prov=[],  # No provenance info in Bear notes
                        annotations=[],  # No annotations in Bear notes
                    )
                    # Create image reference from PIL image
                    item.image = ImageRef.from_pil(img, dpi=72)
                    return item

            elif mime_type == "text/csv":
                self._validate_table(attachment_path)
                df = pd.read_csv(attachment_path)
                table_cells = []
                for i in range(len(df)):
                    for j in range(len(df.columns)):
                        cell = TableCell(
                            text=str(df.iloc[i, j]),
                            start_row_offset_idx=i,
                            end_row_offset_idx=i,
                            start_col_offset_idx=j,
                            end_col_offset_idx=j,
                            column_header=(i == 0),  # First row is header
                            row_header=False,
                            row_section=False,
                        )
                        table_cells.append(cell)

                table_data = TableData(
                    table_cells=table_cells, num_rows=len(df), num_cols=len(df.columns)
                )

                item = TableItem(
                    label=DocItemLabel.TABLE,
                    self_ref=f"#/tables/{attachment_path.name}",
                    captions=[],  # Bear notes don't support captions yet
                    references=[],  # No references in Bear notes
                    footnotes=[],  # No footnotes in Bear notes
                    prov=[],  # No provenance info in Bear notes
                    data=table_data,
                )
                return item

            return None

        except (UnsupportedFormatError, AttachmentError) as e:
            logger.warning(f"Failed to process attachment {attachment_path}: {e}")
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error processing attachment {attachment_path}: {e}"
            )
            return None

    def _process_note_attachments(self, note_dir: Path) -> list[FloatingItem]:
        """Process all attachments in a note directory."""
        attachments = []
        for attachment_path in note_dir.glob("*"):
            if attachment_path.is_file() and attachment_path.name != "text.txt":
                item = self._process_attachment(attachment_path)
                if item:
                    attachments.append(item)
        return attachments

    def process_notes(self) -> list[DoclingDocument]:
        """Process all notes in the input directory."""
        notes = []
        for note_dir in self.input_dir.glob("*"):
            if note_dir.is_dir():
                try:
                    # Process text content
                    text_path = note_dir / "text.txt"
                    if text_path.exists():
                        with open(text_path) as f:
                            text = f.read()

                    # Process attachments
                    attachments = self._process_note_attachments(note_dir)

                    # Create document
                    doc = DoclingDocument(
                        name=note_dir.name,
                        origin=DocumentOrigin(
                            mimetype="text/markdown",
                            binary_hash=self._compute_binary_hash(text_path),
                            filename=text_path.name,
                            uri=AnyUrl.build(
                                scheme="file", host="", path=str(text_path.absolute())
                            ),
                        ),
                    )

                    # Add text content
                    doc.texts.append(
                        TextItem(
                            label=DocItemLabel.TEXT,
                            text=text,
                            orig=text,
                            self_ref="#/texts/0",
                            prov=[],  # No provenance info in Bear notes
                        )
                    )

                    # Add attachments
                    for item in attachments:
                        if isinstance(item, PictureItem):
                            doc.pictures.append(item)
                        elif isinstance(item, TableItem):
                            doc.tables.append(item)

                    notes.append(doc)

                except Exception as e:
                    logger.error(f"Failed to process note {note_dir}: {e}")
                    continue

        return notes

    def _compute_binary_hash(self, file_path: Path) -> int:
        """Compute a binary hash for a file."""
        with open(file_path, "rb") as f:
            content = f.read()
            file_hash = hashlib.sha256(content).digest()[:8]
            return int.from_bytes(file_hash, byteorder="big")
