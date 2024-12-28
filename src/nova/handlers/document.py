"""Document file handler."""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Union
import shutil
import docx
import PyPDF2

from ..models.document import DocumentMetadata
from .base import BaseHandler
from ..config.manager import ConfigManager


class DocumentHandler(BaseHandler):
    """Handler for document files."""
    
    name = "document"
    version = "0.1.0"
    file_types = ["doc", "docx", "pdf", "rtf", "odt"]
    
    def __init__(self, config: ConfigManager) -> None:
        """Initialize document handler.
        
        Args:
            config: Nova configuration manager.
        """
        super().__init__(config)
    
    async def _process_content(self, file_path: Path) -> str:
        """Process document file content.
        
        Args:
            file_path: Path to file.
            
        Returns:
            Processed content.
        """
        try:
            if file_path.suffix.lower() == '.pdf':
                text = []
                with open(file_path, 'rb') as file:
                    # Create PDF reader object
                    pdf_reader = PyPDF2.PdfReader(file)
                    
                    # Extract text from each page
                    for page in pdf_reader.pages:
                        text.append(page.extract_text())
                    
                return "\n\n".join(text)
                
            elif file_path.suffix.lower() == '.docx':
                # Open the document
                doc = docx.Document(file_path)
                
                # Extract text from paragraphs
                text = []
                for para in doc.paragraphs:
                    if para.text.strip():
                        text.append(para.text)
                
                return "\n\n".join(text)
                
            else:
                raise ValueError(f"Unsupported file type: {file_path.suffix}")
                
        except Exception as e:
            return f"Error extracting text: {str(e)}" 
    
    async def process_impl(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: DocumentMetadata,
    ) -> Optional[DocumentMetadata]:
        """Process a document file.
        
        Args:
            file_path: Path to document file.
            output_dir: Directory to write output files.
            metadata: Document metadata.
            
        Returns:
            Document metadata.
        """
        try:
            # Create output directory
            output_dir = Path(str(output_dir))
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create markdown file
            markdown_path = output_dir / f"{file_path.stem}.parsed.md"
            
            # Extract text based on file type
            if file_path.suffix.lower() == '.pdf':
                text = self._extract_pdf_text(file_path)
            elif file_path.suffix.lower() == '.docx':
                text = self._extract_docx_text(file_path)
            else:
                raise ValueError(f"Unsupported document type: {file_path.suffix}")
            
            # Write markdown file with extracted text and reference to original
            self._write_markdown(markdown_path, file_path.stem, file_path, text)
            
            # Update metadata
            metadata.title = file_path.stem
            metadata.metadata['original_path'] = str(file_path)
            metadata.metadata['text'] = text
            metadata.processed = True
            metadata.add_output_file(markdown_path)
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to process document {file_path}: {str(e)}")
            return None 
    
    def _extract_pdf_text(self, file_path: Path) -> str:
        """Extract text from PDF file.
        
        Args:
            file_path: Path to PDF file.
            
        Returns:
            Extracted text from PDF file.
        """
        try:
            # Open PDF file
            with open(file_path, 'rb') as f:
                # Create PDF reader object
                reader = PyPDF2.PdfReader(f)
                
                # Extract text from each page
                text = []
                for page in reader.pages:
                    text.append(page.extract_text())
                
                # Join pages together
                return "\n\n".join(text)
                
        except Exception as e:
            return f"Error extracting text from PDF: {str(e)}"
            
    def _extract_docx_text(self, file_path: Path) -> str:
        """Extract text from DOCX file.
        
        Args:
            file_path: Path to DOCX file.
            
        Returns:
            Extracted text from DOCX file.
        """
        try:
            # Open DOCX file
            doc = docx.Document(file_path)
            
            # Extract text from each paragraph
            text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    text.append(para.text)
                    
            # Join paragraphs together
            return "\n\n".join(text)
            
        except Exception as e:
            return f"Error extracting text from DOCX: {str(e)}" 