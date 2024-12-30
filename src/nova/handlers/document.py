"""Document file handler for processing various document formats.

This handler supports:
- PDF files (.pdf)
- Word documents (.doc, .docx)
- Rich Text Format (.rtf)
- OpenDocument Text (.odt)
- PowerPoint (.pptx)

It extracts text content while preserving structure where possible,
and converts to a standardized Markdown format.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple
import shutil
import docx
import PyPDF2
import pypandoc
import logging
from dataclasses import dataclass
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from ..models.document import DocumentMetadata
from .base import BaseHandler, ProcessingError, ValidationError
from ..config.manager import ConfigManager


@dataclass
class DocumentSection:
    """Represents a section in a document."""
    title: str
    content: str
    level: int = 1
    metadata: Dict[str, any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_markdown(self) -> str:
        """Convert section to markdown."""
        header = "#" * self.level
        return f"{header} {self.title}\n\n{self.content}\n"


class DocumentHandler(BaseHandler):
    """Handler for document files.
    
    Supports multiple document formats and attempts to preserve
    document structure during conversion to Markdown.
    """
    
    name = "document"
    version = "0.2.0"
    file_types = ["pdf", "doc", "docx", "rtf", "odt", "pptx"]
    
    def __init__(self, config: ConfigManager) -> None:
        """Initialize document handler.
        
        Args:
            config: Nova configuration manager
        """
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        
        # Verify pandoc is available for RTF/ODT conversion
        try:
            pypandoc.get_pandoc_version()
        except OSError:
            self.logger.warning("Pandoc not found - RTF/ODT support will be limited")
    
    async def process_impl(
        self,
        file_path: Path,
        metadata: DocumentMetadata,
    ) -> Optional[DocumentMetadata]:
        """Process a document file.
        
        Extracts text and structure from document files and converts
        to Markdown format.
        
        Args:
            file_path: Path to document file
            metadata: Document metadata
            
        Returns:
            Updated metadata, or None if processing failed
            
        Raises:
            ProcessingError: If document processing fails
        """
        try:
            # Get output path
            markdown_path = self.output_manager.get_output_path_for_phase(
                file_path,
                "parse",
                ".parsed.md"
            )
            
            # Extract content based on file type
            sections = []
            
            if file_path.suffix.lower() == '.pdf':
                sections = await self._process_pdf(file_path)
            elif file_path.suffix.lower() in ['.doc', '.docx']:
                sections = await self._process_word(file_path)
            elif file_path.suffix.lower() in ['.rtf', '.odt']:
                sections = await self._process_rtf_odt(file_path)
            elif file_path.suffix.lower() == '.pptx':
                sections = await self._process_powerpoint(file_path)
            else:
                raise ProcessingError(f"Unsupported file type: {file_path.suffix}")
            
            # Convert sections to markdown
            content = self._sections_to_markdown(sections)
            
            # Write markdown file
            self._safe_write_file(markdown_path, content)
            
            # Update metadata
            metadata.title = file_path.stem
            metadata.metadata['original_path'] = str(file_path)
            metadata.metadata['section_count'] = len(sections)
            metadata.processed = True
            metadata.add_output_file(markdown_path)
            
            return metadata
            
        except Exception as e:
            raise ProcessingError(f"Failed to process document {file_path}: {str(e)}") from e
    
    def _sections_to_markdown(self, sections: List[DocumentSection]) -> str:
        """Convert sections to markdown format.
        
        Args:
            sections: List of document sections
            
        Returns:
            Markdown content
        """
        parts = []
        
        # Add summary section
        summary = f"Document containing {len(sections)} sections."
        parts.append("--==SUMMARY==--\n" + summary + "\n")
        
        # Add raw notes section
        parts.append("--==RAW NOTES==--\n")
        for section in sections:
            parts.append(section.to_markdown())
        
        return "\n".join(parts)
    
    async def _process_pdf(self, file_path: Path) -> List[DocumentSection]:
        """Process PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List of document sections
            
        Raises:
            ProcessingError: If PDF processing fails
        """
        try:
            sections = []
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                # Add document info section
                info = reader.metadata
                if info:
                    sections.append(DocumentSection(
                        title="Document Information",
                        content="\n".join(f"- {k}: {v}" for k, v in info.items()),
                        level=1,
                        metadata={'type': 'info'}
                    ))
                
                # Process each page
                for i, page in enumerate(reader.pages, 1):
                    text = page.extract_text()
                    if text.strip():
                        sections.append(DocumentSection(
                            title=f"Page {i}",
                            content=text,
                            level=2,
                            metadata={'page': i}
                        ))
                
            return sections
            
        except Exception as e:
            raise ProcessingError(f"Failed to process PDF: {str(e)}") from e
    
    async def _process_word(self, file_path: Path) -> List[DocumentSection]:
        """Process Word document.
        
        Args:
            file_path: Path to Word document
            
        Returns:
            List of document sections
            
        Raises:
            ProcessingError: If Word processing fails
        """
        try:
            sections = []
            doc = docx.Document(file_path)
            
            # Add document properties
            props = doc.core_properties
            if props:
                sections.append(DocumentSection(
                    title="Document Properties",
                    content="\n".join([
                        f"- Author: {props.author or 'Unknown'}",
                        f"- Created: {props.created or 'Unknown'}",
                        f"- Modified: {props.modified or 'Unknown'}",
                        f"- Title: {props.title or 'Unknown'}",
                    ]),
                    level=1,
                    metadata={'type': 'properties'}
                ))
            
            # Process paragraphs
            current_section = None
            for para in doc.paragraphs:
                if para.style.name.startswith('Heading'):
                    # Start new section
                    if current_section:
                        sections.append(current_section)
                    
                    # Get heading level
                    level = int(para.style.name.replace('Heading', ''))
                    current_section = DocumentSection(
                        title=para.text,
                        content="",
                        level=level
                    )
                elif para.text.strip():
                    # Add to current section or create new one
                    if current_section is None:
                        current_section = DocumentSection(
                            title="Content",
                            content=para.text + "\n\n",
                            level=1
                        )
                    else:
                        current_section.content += para.text + "\n\n"
            
            # Add final section
            if current_section:
                sections.append(current_section)
                
            return sections
            
        except Exception as e:
            raise ProcessingError(f"Failed to process Word document: {str(e)}") from e
    
    async def _process_rtf_odt(self, file_path: Path) -> List[DocumentSection]:
        """Process RTF/ODT document using pandoc.
        
        Args:
            file_path: Path to RTF/ODT file
            
        Returns:
            List of document sections
            
        Raises:
            ProcessingError: If processing fails
        """
        try:
            # Convert to markdown using pandoc
            markdown = pypandoc.convert_file(
                str(file_path),
                'markdown',
                format=file_path.suffix.lstrip('.')
            )
            
            # Split into sections based on headers
            sections = []
            current_section = None
            
            for line in markdown.split('\n'):
                if line.startswith('#'):
                    # New section
                    if current_section:
                        sections.append(current_section)
                    
                    # Count heading level
                    level = len(line.split()[0])
                    title = line.lstrip('#').strip()
                    
                    current_section = DocumentSection(
                        title=title,
                        content="",
                        level=level
                    )
                elif line.strip():
                    # Add to current section or create new one
                    if current_section is None:
                        current_section = DocumentSection(
                            title="Content",
                            content=line + "\n",
                            level=1
                        )
                    else:
                        current_section.content += line + "\n"
            
            # Add final section
            if current_section:
                sections.append(current_section)
                
            return sections
            
        except Exception as e:
            raise ProcessingError(f"Failed to process RTF/ODT: {str(e)}") from e
    
    async def _process_powerpoint(self, file_path: Path) -> List[DocumentSection]:
        """Process PowerPoint presentation.
        
        Args:
            file_path: Path to PowerPoint file
            
        Returns:
            List of document sections
            
        Raises:
            ProcessingError: If processing fails
        """
        try:
            sections = []
            prs = Presentation(file_path)
            
            # Add presentation properties
            if prs.core_properties:
                props = prs.core_properties
                sections.append(DocumentSection(
                    title="Presentation Properties",
                    content="\n".join([
                        f"- Title: {props.title or 'Unknown'}",
                        f"- Author: {props.author or 'Unknown'}",
                        f"- Created: {props.created or 'Unknown'}",
                        f"- Modified: {props.modified or 'Unknown'}",
                        f"- Subject: {props.subject or 'Unknown'}",
                    ]),
                    level=1,
                    metadata={'type': 'properties'}
                ))
            
            # Process each slide
            for slide_num, slide in enumerate(prs.slides, 1):
                # Extract slide title
                title = f"Slide {slide_num}"
                for shape in slide.shapes:
                    if shape.has_text_frame and shape.text.strip():
                        if hasattr(shape, 'is_title') and shape.is_title:
                            title = f"Slide {slide_num}: {shape.text.strip()}"
                            break
                
                # Extract content from shapes
                content_parts = []
                
                # Process shapes
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        text = shape.text.strip()
                        if text and not (hasattr(shape, 'is_title') and shape.is_title):
                            content_parts.append(text)
                    
                    elif shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                        content_parts.append(f"[Image: {shape.name}]")
                        
                    elif shape.shape_type == MSO_SHAPE_TYPE.TABLE:
                        table_rows = []
                        for row in shape.table.rows:
                            cells = [cell.text.strip() for cell in row.cells]
                            table_rows.append("| " + " | ".join(cells) + " |")
                        
                        if table_rows:
                            # Add header separator
                            header_sep = "|" + "|".join(["---"] * len(shape.table.rows[0].cells)) + "|"
                            table_rows.insert(1, header_sep)
                            content_parts.append("\n".join(table_rows))
                
                # Get notes
                notes = None
                if slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip():
                    notes = slide.notes_slide.notes_text_frame.text.strip()
                
                # Create slide section
                content = "\n\n".join(content_parts)
                if notes:
                    content += f"\n\n**Notes:**\n{notes}"
                
                sections.append(DocumentSection(
                    title=title,
                    content=content,
                    level=2,
                    metadata={
                        'type': 'slide',
                        'slide_number': slide_num,
                        'has_notes': bool(notes)
                    }
                ))
            
            return sections
            
        except Exception as e:
            raise ProcessingError(f"Failed to process PowerPoint: {str(e)}") from e 