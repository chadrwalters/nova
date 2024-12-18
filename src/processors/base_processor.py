from pathlib import Path
from typing import Dict, Any
from ..core.logging import get_logger
from ..core.config import NovaConfig
from ..core.errors import ProcessingError, format_error_message
from abc import ABC, abstractmethod

logger = get_logger(__name__)

class BaseDocumentProcessor(ABC):
    """Base class for document processors."""
    
    def __init__(self, config: NovaConfig):
        self.config = config
        
    @abstractmethod
    async def process_document(self, doc_path: Path, title: str, meta: Dict[str, Any]) -> str:
        """
        Process a document and return markdown content.
        
        Args:
            doc_path: Path to the document
            title: Document title
            meta: Document metadata
            
        Returns:
            Markdown content
            
        Raises:
            ProcessingError: If document processing fails
        """
        raise NotImplementedError("Subclasses must implement process_document")
        
    def extract_metadata(self, doc_path: Path) -> Dict[str, Any]:
        """Extract metadata from document."""
        try:
            stats = doc_path.stat()
            return {
                "source_file": str(doc_path),
                "processed_timestamp": stats.st_mtime,
                "file_info": {
                    "size": stats.st_size,
                    "created": stats.st_ctime,
                    "modified": stats.st_mtime
                }
            }
        except Exception as e:
            logger.warning("metadata_extraction_failed",
                         path=str(doc_path),
                         error=str(e))
            return {}
            
    def _format_error(self, error_msg: str, title: str, path: str) -> str:
        """Format error message in markdown."""
        return f"""
> **Error**: {error_msg}
> - Title: {title}
> - Path: {path}
""" 