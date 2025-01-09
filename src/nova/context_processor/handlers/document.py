"""Document handler for Nova document processor."""

import logging
from pathlib import Path
import fitz  # PyMuPDF for PDF handling
import docx  # python-docx for DOCX handling
import io
from typing import Optional, Set

from nova.context_processor.core.metadata import BaseMetadata
from nova.context_processor.core.metadata.models.types import DocumentMetadata
from nova.context_processor.handlers.base import BaseHandler
from nova.context_processor.utils.file_utils import calculate_file_hash

logger = logging.getLogger(__name__)


class DocumentHandler(BaseHandler):
    """Handler for document files."""

    def __init__(self, config):
        """Initialize handler.

        Args:
            config: Nova configuration
        """
        super().__init__(config)
        self.supported_extensions = {
            ".txt",
            ".pdf",
            ".doc",
            ".docx",
        }

    async def _extract_text_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF file.

        Args:
            file_path: Path to PDF file

        Returns:
            str: Extracted text
        """
        try:
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            return text
        except Exception as e:
            logger.error(f"Failed to extract text from PDF {file_path}: {e}")
            return ""

    async def _extract_text_from_docx(self, file_path: Path) -> str:
        """Extract text from DOCX file.

        Args:
            file_path: Path to DOCX file

        Returns:
            str: Extracted text
        """
        try:
            doc = docx.Document(file_path)
            return "\n".join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as e:
            logger.error(f"Failed to extract text from DOCX {file_path}: {e}")
            return ""

    async def _process_file(self, file_path: Path, metadata: DocumentMetadata) -> bool:
        """Process a document file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether processing was successful
        """
        try:
            content = ""
            extension = file_path.suffix.lower()

            if extension == ".pdf":
                content = await self._extract_text_from_pdf(file_path)
            elif extension == ".docx":
                content = await self._extract_text_from_docx(file_path)
            elif extension == ".txt":
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                logger.warning(f"Unsupported document type: {extension}")
                return False

            # Update metadata
            metadata.content = content
            metadata.title = file_path.stem
            metadata.file_size = file_path.stat().st_size
            metadata.file_hash = calculate_file_hash(file_path)
            metadata.word_count = len(content.split())

            return True

        except Exception as e:
            logger.error(f"Failed to process document {file_path}: {e}")
            return False

    async def parse_file(self, file_path: Path) -> Optional[BaseMetadata]:
        """Parse a document file.

        Args:
            file_path: Path to document file

        Returns:
            Optional[BaseMetadata]: Metadata if successful, None if failed
        """
        try:
            # Create metadata
            metadata = BaseMetadata(
                file_path=str(file_path),
                file_name=file_path.name,
                file_type=file_path.suffix.lstrip('.'),
                file_size=file_path.stat().st_size,
                file_hash=self._calculate_file_hash(file_path),
                created_at=file_path.stat().st_ctime,
                modified_at=file_path.stat().st_mtime,
                word_count=0,
                output_files=set(),
            )

            # Process file
            if await self._process_file(file_path, metadata):
                # Update word count if content exists
                if metadata.content:
                    metadata.word_count = len(metadata.content.split())
                return metadata

            return None

        except Exception as e:
            logger.error(f"Failed to parse document file {file_path}: {str(e)}")
            return None

    async def _disassemble_file(self, file_path: Path, metadata: DocumentMetadata) -> bool:
        """Disassemble a document file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether disassembly was successful
        """
        try:
            # For now, just copy the file
            metadata.title = file_path.stem
            metadata.file_size = file_path.stat().st_size
            metadata.file_hash = calculate_file_hash(file_path)

            return True

        except Exception as e:
            logger.error(f"Failed to disassemble document {file_path}: {e}")
            return False

    async def _split_file(self, file_path: Path, metadata: DocumentMetadata) -> bool:
        """Split a document file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether splitting was successful
        """
        try:
            # For now, just copy the file
            metadata.title = file_path.stem
            metadata.file_size = file_path.stat().st_size
            metadata.file_hash = calculate_file_hash(file_path)

            return True

        except Exception as e:
            logger.error(f"Failed to split document {file_path}: {e}")
            return False
