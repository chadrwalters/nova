"""Document file handler."""

import mimetypes
import os
from pathlib import Path
from typing import Dict, List, Optional, Union

from docx import Document as DocxDocument
from pypdf import PdfReader

from ..config.manager import ConfigManager
from ..core.markdown import MarkdownWriter
from ..models.document import DocumentMetadata
from .base import BaseHandler, ProcessingResult, ProcessingStatus


class DocumentHandler(BaseHandler):
    """Handler for document files (PDF, DOCX, etc.)."""

    name = "document"
    version = "0.2.0"
    file_types = ["pdf", "docx", "doc", "odt", "rtf"]

    def __init__(self, config: ConfigManager) -> None:
        """Initialize document handler.

        Args:
            config: Nova configuration manager.
        """
        super().__init__(config)
        self.markdown_writer = MarkdownWriter()

    def _extract_pdf_text(self, file_path: Path) -> str:
        """Extract text from PDF file.

        Args:
            file_path: Path to PDF file.

        Returns:
            Extracted text content.
        """
        try:
            # Open PDF file
            with open(file_path, "rb") as f:
                # Create PDF reader
                reader = PdfReader(f)

                # Extract text from all pages
                text = []
                for page in reader.pages:
                    text.append(page.extract_text())

                return "\n\n".join(text)

        except Exception as e:
            raise ValueError(f"Failed to read file {file_path}: {str(e)}")

    def _extract_docx_text(self, file_path: Path) -> str:
        """Extract text from DOCX file.

        Args:
            file_path: Path to DOCX file.

        Returns:
            Extracted text content.
        """
        try:
            # Open DOCX file
            doc = DocxDocument(file_path)

            # Extract text from paragraphs
            text = []
            for para in doc.paragraphs:
                text.append(para.text)

            return "\n\n".join(text)

        except Exception as e:
            raise ValueError(f"Failed to read file {file_path}: {str(e)}")

    async def process_file_impl(
        self,
        file_path: Path,
        output_path: Path,
        metadata: DocumentMetadata,
    ) -> Optional[DocumentMetadata]:
        """Process a document file.

        Args:
            file_path: Path to document file.
            output_path: Path to write output.
            metadata: Document metadata.

        Returns:
            Document metadata.
        """
        try:
            # Extract text based on file type
            if file_path.suffix.lower() == ".pdf":
                content = self._extract_pdf_text(file_path)
            elif file_path.suffix.lower() in [".docx", ".doc"]:
                content = self._extract_docx_text(file_path)
            else:
                raise ValueError(f"Unsupported document type: {file_path.suffix}")

            # Update metadata
            metadata.title = file_path.stem
            metadata.processed = True
            metadata.metadata.update(
                {
                    "file_type": mimetypes.guess_type(file_path)[0]
                    or f"application/{file_path.suffix.lstrip('.')}",
                    "content_length": len(content),
                }
            )

            # Create document marker
            doc_type = "PDF" if file_path.suffix.lower() == ".pdf" else "DOC"
            doc_marker = f"[ATTACH:{doc_type}:{file_path.stem}]"

            # Write markdown using MarkdownWriter
            markdown_content = self.markdown_writer.write_document(
                title=metadata.title,
                content=f"{doc_marker}\n\n{content}",
                metadata=metadata.metadata,
                file_path=file_path,
                output_path=output_path,
            )

            # Write the file
            self._safe_write_file(output_path, markdown_content)

            metadata.add_output_file(output_path)
            return metadata

        except Exception as e:
            error_msg = f"Failed to process document {file_path}: {str(e)}"
            self.logger.error(error_msg)
            if metadata:
                metadata.add_error(self.name, error_msg)
                metadata.processed = False
            return metadata
