from pathlib import Path
import os
import re
import json
import structlog
import aiofiles
from typing import Dict, Any, Tuple, Optional
from docx import Document
from docx.shared import Inches
from docx.oxml.shared import qn
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph
from docx.table import Table
from .base_processor import BaseDocumentProcessor
from ..core.errors import ProcessingError, ErrorSeverity, format_error_message
from ..core.config import NovaConfig
from datetime import datetime
from ..core.logging import get_logger

logger = get_logger(__name__)

class WordProcessor(BaseDocumentProcessor):
    """Process Word documents."""
    
    def __init__(self, config: NovaConfig):
        super().__init__(config)
        self.image_output_dir = Path(config.document_handling.word_processing["image_output_dir"])
        self.preserve_images = config.document_handling.word_processing["preserve_images"]
        self.max_image_size = config.document_handling.word_processing["max_image_size"]
        
    async def process_document(self, doc_path: Path, title: str, meta: Dict[str, Any]) -> str:
        """Process a Word document and return markdown content."""
        try:
            # Extract metadata
            doc_meta = self.extract_metadata(doc_path)
            
            # Convert to markdown using markitdown
            markdown = await self._convert_to_markdown(doc_path)
            
            # Format the output with metadata
            output = f"""---
title: {doc_meta.get('title', title)}
author: {doc_meta.get('author', 'Unknown')}
date: {doc_meta.get('modified') or doc_meta.get('created') or datetime.utcnow().isoformat()}
source: {str(doc_path)}
---

{markdown}
"""
            return output
                
        except Exception as e:
            logger.error("word_processing_failed",
                        path=str(doc_path),
                        error=str(e))
            return format_error_message(str(e), title, str(doc_path))
    
    def _extract_metadata(self, doc: Document) -> Dict[str, Any]:
        """Extract metadata from Word document."""
        metadata = {
            "author": doc.core_properties.author or "",
            "title": doc.core_properties.title or "",
            "created": doc.core_properties.created.isoformat() if doc.core_properties.created else "",
            "modified": doc.core_properties.modified.isoformat() if doc.core_properties.modified else "",
            "revision": doc.core_properties.revision or 1,
            "word_count": len(doc.paragraphs)
        }
        return metadata
        
    async def _process_paragraph(self, para: Paragraph) -> str:
        """Process a paragraph and return markdown."""
        try:
            # Skip empty paragraphs
            if not para.text.strip():
                return ""
                
            # Get paragraph style
            style = para.style.name.lower()
            
            # Process heading styles
            if style.startswith('heading'):
                level = int(style[-1])
                return f"{'#' * level} {para.text}"
                
            # Process list items
            if style.startswith('list'):
                return f"- {para.text}"
                
            # Process images
            for run in para.runs:
                if run._element.drawing_lst:
                    return await self._process_image(run)
                    
            # Default paragraph processing
            text = para.text.strip()
            
            # Handle basic formatting
            text = self._process_formatting(text, para)
            
            return text
            
        except Exception as e:
            logger.error("paragraph_processing_failed", error=str(e))
            return para.text
            
    async def _process_table(self, table: Table) -> str:
        """Process a table and return markdown."""
        try:
            rows = []
            
            # Process header row
            header = []
            for cell in table.rows[0].cells:
                header.append(cell.text.strip() or " ")
            rows.append("| " + " | ".join(header) + " |")
            
            # Add separator row
            rows.append("| " + " | ".join(["---"] * len(header)) + " |")
            
            # Process data rows
            for row in table.rows[1:]:
                cells = []
                for cell in row.cells:
                    cells.append(cell.text.strip() or " ")
                rows.append("| " + " | ".join(cells) + " |")
                
            return "\n".join(rows)
            
        except Exception as e:
            logger.error("table_processing_failed", error=str(e))
            return ""
            
    async def _process_image(self, run) -> str:
        """Process an image and return markdown."""
        try:
            # Extract image data
            image_data = run._element.drawing_lst[0]
            
            # Generate unique filename
            image_id = image_data.attrib.get('id', 'image')
            filename = f"{image_id}.png"
            
            if self.preserve_images:
                # Save image to assets directory
                image_path = self.image_output_dir / filename
                image_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write image data
                async with aiofiles.open(image_path, 'wb') as f:
                    await f.write(image_data.blob)
                    
                # Return markdown image reference
                return f"![{image_id}]({image_path.relative_to(self.image_output_dir)})"
            else:
                # Return placeholder text
                return f"[Image: {image_id}]"
                
        except Exception as e:
            logger.error("image_processing_failed", error=str(e))
            return "[Image processing failed]"
            
    def _process_formatting(self, text: str, para: Paragraph) -> str:
        """Process text formatting."""
        # Handle bold
        if para.style.font.bold:
            text = f"**{text}**"
            
        # Handle italic
        if para.style.font.italic:
            text = f"*{text}*"
            
        # Handle underline
        if para.style.font.underline:
            text = f"__{text}__"
            
        # Handle strikethrough
        if para.style.font.strike:
            text = f"~~{text}~~"
            
        return text 