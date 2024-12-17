import asyncio
from pathlib import Path
import structlog
from typing import List, Optional, Dict, Any
import aiofiles
import re
from datetime import datetime

from src.core.models import (
    ProcessedDocument,
    Attachment,
    AttachmentType,
    ProcessingConfig
)
from src.core.exceptions import ProcessingError, ValidationError
from src.processors.attachment_processor import AttachmentProcessor

logger = structlog.get_logger(__name__)

class IndividualProcessor:
    """Processes individual markdown documents."""

    def __init__(self, config: ProcessingConfig):
        """Initialize the processor.
        
        Args:
            config: Processing configuration
        """
        self.config = config
        self.attachment_processor = AttachmentProcessor(
            media_dir=config.processing_dir / "attachments",
            error_tolerance=config.error_tolerance == "lenient"
        )

    async def process_document(self, file_path: Path) -> ProcessedDocument:
        """Process a single markdown document.
        
        Args:
            file_path: Path to markdown file
            
        Returns:
            ProcessedDocument with processed content and attachments
            
        Raises:
            ProcessingError: If processing fails
        """
        try:
            # Validate file
            await self._validate_file(file_path)
            
            # Read content
            content = await self._read_file(file_path)
            
            # Extract metadata
            metadata = await self._extract_metadata(content)
            
            # Process attachments
            content, attachments = await self._process_attachments(content, file_path)
            
            # Generate processed path
            processed_path = self._get_processed_path(file_path)
            
            # Create processed document
            doc = ProcessedDocument(
                content=content,
                source_path=file_path,
                processed_path=processed_path,
                attachments=attachments,
                metadata=metadata,
                processing_date=datetime.now()
            )
            
            # Save processed document
            await self._save_processed_document(doc)
            
            return doc
            
        except Exception as e:
            raise ProcessingError(
                f"Failed to process document {file_path}: {str(e)}",
                stage="individual_processing"
            )

    async def _validate_file(self, file_path: Path) -> None:
        """Validate the input file.
        
        Args:
            file_path: Path to file to validate
            
        Raises:
            ValidationError: If validation fails
        """
        if not file_path.exists():
            raise ValidationError(f"File does not exist: {file_path}")
            
        if file_path.suffix.lower() != ".md":
            raise ValidationError(f"Not a markdown file: {file_path}")
            
        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > self.config.max_file_size_mb:
            raise ValidationError(
                f"File too large: {size_mb:.1f}MB > {self.config.max_file_size_mb}MB"
            )

    async def _read_file(self, file_path: Path) -> str:
        """Read file content.
        
        Args:
            file_path: Path to file to read
            
        Returns:
            File content as string
        """
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            return await f.read()

    async def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from markdown content.
        
        Args:
            content: Markdown content
            
        Returns:
            Dictionary of metadata
        """
        metadata = {}
        
        # Look for YAML frontmatter between --- markers
        if content.startswith('---'):
            try:
                end = content.index('---', 3)
                frontmatter = content[3:end].strip()
                
                # Parse YAML frontmatter
                import yaml
                metadata = yaml.safe_load(frontmatter)
                
            except Exception as e:
                logger.warning(
                    "Failed to parse frontmatter",
                    error=str(e)
                )
                
        return metadata or {}

    async def _process_attachments(
        self,
        content: str,
        source_path: Path
    ) -> tuple[str, List[Attachment]]:
        """Process attachments referenced in the content.
        
        Args:
            content: Markdown content
            source_path: Path to source document
            
        Returns:
            Tuple of (updated content, list of attachments)
        """
        attachments = []
        updated_content = content
        
        # Find all markdown link references
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        for match in re.finditer(link_pattern, content):
            link_text, link_path = match.groups()
            
            # Convert to Path and resolve relative to source
            link_path = Path(link_path)
            if not link_path.is_absolute():
                link_path = source_path.parent / link_path
                
            try:
                # Process attachment if it exists
                if link_path.exists():
                    attachment = await self.attachment_processor.process_attachment(
                        link_path
                    )
                    if attachment:
                        attachments.append(attachment)
                        
                        # Update link in content
                        rel_path = Path("..") / "attachments" / attachment.processed_path.name
                        updated_content = updated_content.replace(
                            match.group(2),
                            str(rel_path)
                        )
                        
            except Exception as e:
                logger.warning(
                    "Failed to process attachment",
                    path=str(link_path),
                    error=str(e)
                )
                
        return updated_content, attachments

    def _get_processed_path(self, source_path: Path) -> Path:
        """Generate path for processed document.
        
        Args:
            source_path: Original file path
            
        Returns:
            Path for processed document
        """
        rel_path = source_path.relative_to(self.config.input_dir)
        return self.config.processing_dir / "individual" / rel_path

    async def _save_processed_document(self, doc: ProcessedDocument) -> None:
        """Save processed document.
        
        Args:
            doc: Processed document to save
        """
        # Create parent directory
        doc.processed_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save content
        async with aiofiles.open(doc.processed_path, 'w', encoding='utf-8') as f:
            await f.write(doc.content) 