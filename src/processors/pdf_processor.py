from pathlib import Path
import structlog
from typing import Dict, Any
import fitz  # PyMuPDF
from datetime import datetime
import aiofiles
import asyncio
from .base_processor import BaseDocumentProcessor
from ..core.errors import ProcessingError, format_error_message
from ..core.logging import get_logger

logger = get_logger(__name__)

class PDFProcessor(BaseDocumentProcessor):
    """Process PDF documents using PyMuPDF"""
    
    def __init__(self, config):
        super().__init__(config)
        
        # Store config for our own use
        self.extract_images = config.document_handling.pdf_processing.get("extract_images", True)
        self.ocr_enabled = config.document_handling.pdf_processing.get("ocr_enabled", True)
        self.temp_dir = config.processing.temp_dir
        
        logger.info("pdf_processor_initialized",
                   extract_images=self.extract_images,
                   ocr_enabled=self.ocr_enabled,
                   temp_dir=self.temp_dir)
        
    async def process_document(self, doc_path: Path, title: str, meta: Dict[str, Any]) -> str:
        """Process PDF document and return markdown content."""
        try:
            logger.info("processing_pdf_document", path=str(doc_path))
            
            # Validate document exists
            if not doc_path.exists():
                return format_error_message("Document not found", title, str(doc_path))
                
            # Open PDF with PyMuPDF
            doc = fitz.open(str(doc_path))
            
            # Extract metadata
            doc_meta = self._extract_metadata(doc_path)
            doc_meta.update({
                "pdf_document": True,
                "processor": "pdf2md",
                "title": doc.metadata.get("title", title),
                "author": doc.metadata.get("author", "Unknown"),
                "subject": doc.metadata.get("subject"),
                "keywords": doc.metadata.get("keywords"),
                "creator": doc.metadata.get("creator"),
                "producer": doc.metadata.get("producer"),
                "pages": len(doc)
            })
            
            # Convert PDF to markdown
            markdown = []
            
            # Add metadata block
            markdown.append(f"""---
title: {doc_meta.get('title', title)}
author: {doc_meta.get('author', 'Unknown')}
date: {doc_meta.get('modified') or doc_meta.get('created') or datetime.utcnow().isoformat()}
source: {str(doc_path)}
pages: {doc_meta['pages']}
---
""")
            
            # Process each page
            tasks = []
            for page_num in range(len(doc)):
                tasks.append(self._process_page(doc, page_num))
            
            # Wait for all pages to be processed
            page_contents = await asyncio.gather(*tasks)
            markdown.extend(page_contents)
            
            # Close the document
            doc.close()
            
            return "\n".join(markdown)
            
        except Exception as e:
            logger.error("pdf_processing_failed",
                        path=str(doc_path),
                        error=str(e))
            return format_error_message(str(e), title, str(doc_path))
            
    async def _process_page(self, doc: fitz.Document, page_num: int) -> str:
        """Process a single PDF page."""
        try:
            page = doc[page_num]
            content = []
            
            # Add page header
            content.append(f"\n## Page {page_num + 1}\n")
            
            # Extract text
            text = page.get_text()
            if text.strip():
                content.append(text)
                
            # Extract images if enabled
            if self.extract_images:
                image_list = page.get_images()
                if image_list:
                    content.append("\n### Images\n")
                    image_tasks = []
                    for img_index, img in enumerate(image_list):
                        image_tasks.append(self._process_image(doc, page_num, img_index, img))
                    
                    # Wait for all images to be processed
                    image_contents = await asyncio.gather(*image_tasks, return_exceptions=True)
                    for img_content in image_contents:
                        if isinstance(img_content, Exception):
                            logger.warning("image_processing_failed", error=str(img_content))
                        elif img_content:
                            content.append(img_content)
                            
            return "\n".join(content)
            
        except Exception as e:
            logger.error("page_processing_failed",
                        page=page_num,
                        error=str(e))
            return f"\n## Page {page_num + 1}\n\n[Error processing page: {str(e)}]\n"
            
    async def _process_image(self, doc: fitz.Document, page_num: int, img_index: int, img: tuple) -> str:
        """Process a single image from a PDF page."""
        try:
            xref = img[0]
            base_image = doc.extract_image(xref)
            if base_image:
                # Save image to temp dir
                img_path = Path(self.temp_dir) / f"page_{page_num + 1}_img_{img_index + 1}.{base_image['ext']}"
                async with aiofiles.open(img_path, "wb") as f:
                    await f.write(base_image["image"])
                return f"\n![Image {img_index + 1} from page {page_num + 1}]({img_path})\n"
            return ""
            
        except Exception as e:
            logger.warning("image_extraction_failed",
                         page=page_num,
                         image=img_index,
                         error=str(e))
            return "" 