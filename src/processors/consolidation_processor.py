import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import structlog
import aiofiles
from datetime import datetime
import re

from src.core.models import (
    ProcessedDocument,
    ConsolidatedDocument,
    ProcessingConfig
)
from src.core.exceptions import ConsolidationError

logger = structlog.get_logger(__name__)

class ConsolidationProcessor:
    """Consolidates multiple processed documents into a single document."""

    def __init__(self, config: ProcessingConfig):
        """Initialize the consolidation processor.
        
        Args:
            config: Processing configuration
        """
        self.config = config
        self.consolidated_dir = config.processing_dir / "consolidated"
        self.consolidated_dir.mkdir(parents=True, exist_ok=True)

    async def consolidate(
        self,
        documents: List[ProcessedDocument]
    ) -> ConsolidatedDocument:
        """Consolidate multiple documents into one.
        
        Args:
            documents: List of processed documents to consolidate
            
        Returns:
            Consolidated document
            
        Raises:
            ConsolidationError: If consolidation fails
        """
        try:
            # Sort documents
            sorted_docs = self._sort_documents(documents)
            
            # Combine content
            content = await self._combine_content(sorted_docs)
            
            # Update internal references
            content = await self._update_references(content, sorted_docs)
            
            # Generate consolidated path
            consolidated_path = self.consolidated_dir / "consolidated.md"
            
            # Create consolidated document
            consolidated = ConsolidatedDocument(
                content=content,
                documents=sorted_docs,
                attachments=[
                    att for doc in sorted_docs 
                    for att in doc.attachments
                ],
                metadata=self._merge_metadata(sorted_docs),
                processing_date=datetime.now()
            )
            
            # Save consolidated document
            await self._save_consolidated(consolidated, consolidated_path)
            
            return consolidated
            
        except Exception as e:
            raise ConsolidationError(
                f"Failed to consolidate documents: {str(e)}",
                stage="consolidation"
            )

    def _sort_documents(
        self,
        documents: List[ProcessedDocument]
    ) -> List[ProcessedDocument]:
        """Sort documents based on path structure.
        
        Args:
            documents: Documents to sort
            
        Returns:
            Sorted list of documents
        """
        def get_sort_key(doc: ProcessedDocument) -> tuple:
            # Get relative path from input directory
            rel_path = doc.source_path.relative_to(self.config.input_dir)
            
            # Split path into parts
            parts = rel_path.parts
            
            # Extract numeric prefixes for sorting
            def extract_number(s: str) -> tuple[int, str]:
                match = re.match(r'^(\d+)_?(.*)', s)
                if match:
                    return (int(match.group(1)), match.group(2))
                return (float('inf'), s)
            
            # Convert each part to a sortable tuple
            return tuple(extract_number(part) for part in parts)
        
        return sorted(documents, key=get_sort_key)

    async def _combine_content(
        self,
        documents: List[ProcessedDocument]
    ) -> str:
        """Combine document content with proper spacing and headers.
        
        Args:
            documents: Documents to combine
            
        Returns:
            Combined content
        """
        sections = []
        
        for doc in documents:
            # Get relative path for section header
            rel_path = doc.source_path.relative_to(self.config.input_dir)
            
            # Create section header
            header = f"\n# {rel_path.stem}\n"
            
            # Add content with proper spacing
            sections.extend([
                header,
                doc.content.strip(),
                "\n---\n"  # Section separator
            ])
        
        return "\n".join(sections)

    async def _update_references(
        self,
        content: str,
        documents: List[ProcessedDocument]
    ) -> str:
        """Update internal references between documents.
        
        Args:
            content: Combined content
            documents: Source documents
            
        Returns:
            Content with updated references
        """
        updated_content = content
        
        # Build reference map
        ref_map = {}
        for doc in documents:
            rel_source = doc.source_path.relative_to(self.config.input_dir)
            rel_processed = doc.processed_path.relative_to(self.config.processing_dir)
            ref_map[str(rel_source)] = str(rel_processed)
        
        # Update references
        for original, processed in ref_map.items():
            # Update markdown links
            updated_content = re.sub(
                f'\\[([^\\]]*)\\]\\({re.escape(original)}\\)',
                f'[\\1]({processed})',
                updated_content
            )
        
        return updated_content

    def _merge_metadata(
        self,
        documents: List[ProcessedDocument]
    ) -> Dict[str, Any]:
        """Merge metadata from all documents.
        
        Args:
            documents: Source documents
            
        Returns:
            Merged metadata
        """
        merged = {
            'title': 'Consolidated Document',
            'date': datetime.now(),
            'source_documents': len(documents),
            'total_attachments': sum(len(doc.attachments) for doc in documents)
        }
        
        # Collect all unique authors
        authors = set()
        for doc in documents:
            if 'author' in doc.metadata:
                authors.add(doc.metadata['author'])
        if authors:
            merged['authors'] = list(authors)
        
        # Collect all unique tags/keywords
        tags = set()
        for doc in documents:
            if 'tags' in doc.metadata:
                tags.update(doc.metadata['tags'])
            if 'keywords' in doc.metadata:
                tags.update(doc.metadata['keywords'])
        if tags:
            merged['tags'] = list(tags)
        
        return merged

    async def _save_consolidated(
        self,
        consolidated: ConsolidatedDocument,
        output_path: Path
    ) -> None:
        """Save consolidated document.
        
        Args:
            consolidated: Consolidated document to save
            output_path: Path to save to
        """
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Add metadata as YAML frontmatter
        import yaml
        frontmatter = yaml.dump(consolidated.metadata, default_flow_style=False)
        content = f"---\n{frontmatter}---\n\n{consolidated.content}"
        
        # Save file
        async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
            await f.write(content) 