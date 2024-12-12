import hashlib
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import PyPDF2
import structlog
import aiofiles

from src.core.exceptions import ProcessingError
from src.processors.attachment_processor import ProcessedAttachment

logger = structlog.get_logger(__name__)


@dataclass
class PDFMetadata:
    """Metadata for PDF attachments."""
    page_count: int
    title: str
    author: str
    creation_date: datetime
    modification_date: datetime
    size: int
    hash: str


class PDFAttachmentHandler:
    """Handles PDF attachment processing and validation."""

    def __init__(self, processing_dir: Path, max_size_mb: int = 50) -> None:
        """Initialize PDF attachment handler.

        Args:
            processing_dir: Directory for processed PDFs
            max_size_mb: Maximum allowed PDF size in MB
        """
        self.processing_dir = processing_dir / "attachments" / "pdf"
        self.processing_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.logger = logger

    def validate_pdf(self, file_path: Path) -> bool:
        """Validate PDF file.

        Args:
            file_path: Path to PDF file

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check file exists
            if not file_path.exists():
                self.logger.error("PDF file not found", path=str(file_path))
                return False

            # Check size
            size = file_path.stat().st_size
            if size > self.max_size_bytes:
                self.logger.error(
                    "PDF file too large",
                    path=str(file_path),
                    size=size,
                    max_size=self.max_size_bytes
                )
                return False

            # Verify PDF structure
            with open(file_path, 'rb') as pdf_file:
                try:
                    pdf = PyPDF2.PdfReader(pdf_file)
                    # Basic structure check
                    _ = len(pdf.pages)
                    return True
                except Exception as e:
                    self.logger.error(
                        "Invalid PDF structure",
                        path=str(file_path),
                        error=str(e)
                    )
                    return False

        except Exception as e:
            self.logger.error(
                "PDF validation failed",
                path=str(file_path),
                error=str(e)
            )
            return False

    def extract_metadata(self, file_path: Path) -> PDFMetadata:
        """Extract metadata from PDF.

        Args:
            file_path: Path to PDF file

        Returns:
            PDFMetadata object

        Raises:
            ProcessingError: If metadata extraction fails
        """
        try:
            with open(file_path, 'rb') as pdf_file:
                pdf = PyPDF2.PdfReader(pdf_file)
                info = pdf.metadata if pdf.metadata else {}
                
                # Calculate file hash
                pdf_file.seek(0)
                content = pdf_file.read()
                file_hash = hashlib.sha256(content).hexdigest()[:12]

                return PDFMetadata(
                    page_count=len(pdf.pages),
                    title=info.get('/Title', file_path.stem),
                    author=info.get('/Author', 'Unknown'),
                    creation_date=info.get('/CreationDate', datetime.now()),
                    modification_date=info.get('/ModDate', datetime.now()),
                    size=file_path.stat().st_size,
                    hash=file_hash
                )

        except Exception as e:
            raise ProcessingError(f"Failed to extract PDF metadata: {e}")

    async def process_pdf(self, file_path: Path) -> ProcessedAttachment:
        """Process PDF attachment.

        Args:
            file_path: Path to PDF file

        Returns:
            ProcessedAttachment object

        Raises:
            ProcessingError: If processing fails
        """
        try:
            # Ensure file exists
            if not file_path.exists():
                raise ProcessingError(f"PDF file not found: {file_path}")

            # Validate PDF
            if not self.validate_pdf(file_path):
                raise ProcessingError(f"Invalid PDF file: {file_path}")

            # Extract metadata
            metadata = self.extract_metadata(file_path)

            # Generate target path with hash
            safe_name = "".join(c if c.isalnum() or c in ".-_" else "_" for c in file_path.stem)
            target_name = f"{safe_name}_{metadata.hash}.pdf"
            target_path = self.processing_dir / target_name

            # Create target directory if it doesn't exist
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file to processing directory
            await self._copy_file(file_path, target_path)

            self.logger.info("PDF file copied to processing directory",
                           source=str(file_path),
                           target=str(target_path),
                           size=metadata.size)

            return ProcessedAttachment(
                source_path=file_path,
                target_path=target_path,
                size=metadata.size,
                metadata={
                    "title": metadata.title,
                    "author": metadata.author,
                    "pages": metadata.page_count,
                    "created": metadata.creation_date,
                    "modified": metadata.modification_date,
                    "hash": metadata.hash
                }
            )

        except Exception as e:
            raise ProcessingError(f"Failed to process PDF attachment: {e}")

    async def _copy_file(self, source: Path, target: Path) -> None:
        """Copy file using async operations.
        
        Args:
            source: Source file path
            target: Target file path
        """
        async with aiofiles.open(source, 'rb') as src, \
                   aiofiles.open(target, 'wb') as dst:
            while chunk := await src.read(8192):  # 8KB chunks
                await dst.write(chunk)

    def update_pdf_references(self, content: str, pdf_map: dict[str, Path]) -> str:
        """Update PDF references in markdown content.

        Args:
            content: Markdown content
            pdf_map: Mapping of original PDF paths to processed paths

        Returns:
            Updated markdown content
        """
        updated_content = content

        # Update inline-style links
        for original_path, processed_path in pdf_map.items():
            # Handle both relative and absolute paths
            original_name = Path(original_path).name
            relative_path = f"../attachments/pdf/{processed_path.name}"
            
            # Replace references
            updated_content = updated_content.replace(
                f"]({original_path})",
                f"]({relative_path})"
            )
            updated_content = updated_content.replace(
                f"](./{original_name})",
                f"]({relative_path})"
            )
            updated_content = updated_content.replace(
                f"](../{original_name})",
                f"]({relative_path})"
            )
            updated_content = updated_content.replace(
                f"](../../{original_name})",
                f"]({relative_path})"
            )

        return updated_content 