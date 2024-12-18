from pathlib import Path
from .logging import get_logger
from markitdown import MarkItDown
from typing import Dict, Any
import os
from datetime import datetime
from ..processors.base_processor import BaseDocumentProcessor
from .errors import ProcessingError

logger = get_logger(__name__)

class WordProcessor(BaseDocumentProcessor):
    """Process Word documents using Microsoft's MarkItDown"""
    
    def __init__(self, config):
        super().__init__(config)
        
        # Initialize MarkItDown with config
        self.converter = MarkItDown()
        
        # Store config for our own use
        self.preserve_images = config.document_handling.word_processing.get("preserve_images", True)
        self.ocr_enabled = config.document_handling.word_processing.get("ocr_enabled", True)
        self.temp_dir = config.processing.temp_dir
        
        logger.info("word_processor_initialized", 
                   preserve_images=self.preserve_images,
                   ocr_enabled=self.ocr_enabled,
                   temp_dir=self.temp_dir)
        
    async def process_document(self, doc_path: Path, title: str, meta: Dict[str, Any]) -> str:
        """Process Word document and return markdown content."""
        try:
            logger.info("processing_word_document", path=str(doc_path))
            
            # Validate document exists
            if not doc_path.exists():
                return self._format_error("Document not found", title, str(doc_path))
                
            # Convert using MarkItDown
            result = self.converter.convert(str(doc_path))
            
            # Get the markdown content
            if hasattr(result, 'text_content'):
                markdown = result.text_content
            else:
                logger.warning("text_content_not_found",
                             type=type(result),
                             path=str(doc_path))
                markdown = str(result)
            
            if not isinstance(markdown, str):
                logger.warning("unexpected_result_type",
                             type=type(result),
                             path=str(doc_path))
                markdown = str(result)
                
            # Extract metadata
            doc_meta = self._extract_metadata(doc_path)
            
            # Try to extract Word document properties
            try:
                from docx import Document
                doc = Document(doc_path)
                core_props = doc.core_properties
                doc_meta.update({
                    "word_document": True,
                    "processor": "markitdown",
                    "title": core_props.title or title,
                    "author": core_props.author,
                    "created": core_props.created.isoformat() if core_props.created else None,
                    "modified": core_props.modified.isoformat() if core_props.modified else None,
                    "revision": core_props.revision
                })
            except Exception as e:
                logger.warning("word_metadata_extraction_failed",
                             path=str(doc_path),
                             error=str(e))
            
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
            return self._format_error(str(e), title, str(doc_path))