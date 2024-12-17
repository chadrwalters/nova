import asyncio
import shutil
from pathlib import Path
import structlog
from typing import Optional, Dict, Any, Tuple, List
import aiofiles
import magic
import hashlib
from datetime import datetime
import base64
import re
import json
import urllib.parse

from src.core.models import Attachment, AttachmentType
from src.core.exceptions import ProcessingError
from src.processors.models import ProcessedAttachment
from src.processors.converters.word_converter import WordConverter
from src.processors.converters.pdf_converter import PDFConverter
from src.processors.converters.powerpoint_converter import PowerPointConverter
from src.processors.converters.image_converter import ImageConverter
from src.generators.pdf_generator import PDFGenerator

logger = structlog.get_logger(__name__)

class AttachmentProcessor:
    """Processes attachments in markdown content."""
    
    SUPPORTED_TYPES = {
        # Images
        '.png': AttachmentType.IMAGE,
        '.jpg': AttachmentType.IMAGE,
        '.jpeg': AttachmentType.IMAGE,
        '.gif': AttachmentType.IMAGE,
        '.webp': AttachmentType.IMAGE,
        '.heic': AttachmentType.IMAGE,
        # Documents
        '.pdf': AttachmentType.PDF,
        '.docx': AttachmentType.WORD,
        '.doc': AttachmentType.WORD,
        '.pptx': AttachmentType.POWERPOINT,
        '.ppt': AttachmentType.POWERPOINT
    }

    async def process_attachments(
        self,
        content: str,
        base_path: Path,
        temp_dir: Path,
        pdf_generator: Optional[PDFGenerator] = None
    ) -> Tuple[str, List[Path]]:
        """Process all attachments in markdown content."""
        processed = []
        result = content

        # Create directories
        images_dir = self.media_dir / "images"
        docs_dir = self.media_dir / "documents"
        images_dir.mkdir(exist_ok=True)
        docs_dir.mkdir(exist_ok=True)

        # Process base64 images
        result, base64_files = await self._process_base64_images(
            result, 
            images_dir,
            pdf_generator
        )
        processed.extend(base64_files)

        # Process file attachments with metadata
        result, doc_files = await self._process_attachments_with_metadata(
            result, 
            base_path, 
            docs_dir,
            pdf_generator
        )
        processed.extend(doc_files)

        return result, processed

    async def _process_base64_images(
        self,
        content: str,
        images_dir: Path,
        pdf_generator: Optional[PDFGenerator] = None
    ) -> Tuple[str, List[Path]]:
        """Process base64 encoded images."""
        processed = []
        result = content
        
        logger.info("Processing base64 images")
        base64_pattern = r'!\[([^\]]*)\]\(data:image/([^;]+);base64,([^)]+)\)'
        matches = list(re.finditer(base64_pattern, content))
        logger.info(f"Found {len(matches)} base64 images")
        
        for match in matches:
            alt_text, image_format, image_data = match.groups()
            logger.info(
                "Processing base64 image",
                alt_text=alt_text,
                format=image_format
            )
            
            try:
                # Save image to file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"image_{timestamp}_{len(processed)}.{image_format}"
                target_path = images_dir / filename
                
                # Save image
                image_bytes = base64.b64decode(image_data)
                async with aiofiles.open(target_path, 'wb') as f:
                    await f.write(image_bytes)
                
                processed.append(target_path)
                
                # Use relative path for image
                rel_path = target_path.relative_to(self.media_dir.parent)
                markdown = f'![{alt_text}]({rel_path})'
                
                result = result.replace(match.group(0), markdown)
                
                logger.info(
                    "Successfully processed base64 image",
                    path=str(target_path)
                )
                
            except Exception as e:
                logger.error(
                    "Failed to process base64 image",
                    format=image_format,
                    error=str(e)
                )
                continue

        return result, processed

    async def _process_attachments_with_metadata(
        self,
        content: str,
        base_path: Path,
        docs_dir: Path,
        pdf_generator: Optional[PDFGenerator] = None
    ) -> Tuple[str, List[Path]]:
        """Process file attachments with metadata."""
        processed = []
        result = content
        
        logger.info("Processing attachments with metadata")
        # Look for markdown links with metadata comments
        attachment_pattern = r'\[([^\]]+)\]\(([^)]+)\)<!-- (\{[^}]+\}) -->'
        matches = list(re.finditer(attachment_pattern, content))
        logger.info(f"Found {len(matches)} attachments")
        
        for match in matches:
            title, path, metadata = match.groups()
            meta = json.loads(metadata)
            
            logger.info(
                "Processing attachment",
                title=title,
                path=path,
                metadata=meta
            )
            
            try:
                # Find actual file
                decoded_path = urllib.parse.unquote(path)
                file_path = Path(decoded_path)
                full_path = await self._find_attachment(file_path, base_path)
                
                if not full_path or not full_path.exists():
                    logger.warning(
                        "Attachment not found",
                        path=str(file_path),
                        search_path=str(base_path)
                    )
                    continue

                # Copy file and update link
                suffix = full_path.suffix.lower()
                if suffix in self.SUPPORTED_TYPES:
                    target_path = docs_dir / file_path.name
                    await self._copy_file(full_path, target_path)
                    processed.append(target_path)
                    
                    rel_path = target_path.relative_to(self.media_dir.parent)
                    new_markdown = f'[{title}]({rel_path})'
                    
                    # Add any special formatting directives
                    if meta.get("preview"):
                        new_markdown = f'> {new_markdown}\n> *Preview*'
                    elif meta.get("embed"):
                        new_markdown = f'\n---\n{new_markdown}\n---\n'
                    
                    result = result.replace(match.group(0), new_markdown)
                    logger.info(
                        "Successfully processed attachment",
                        path=str(full_path),
                        target=str(target_path)
                    )
                    
            except Exception as e:
                logger.error(
                    "Failed to process attachment",
                    title=title,
                    path=path,
                    error=str(e)
                )

        return result, processed

    async def _find_attachment(self, file_path: Path, base_path: Path) -> Optional[Path]:
        """Find attachment file using various search paths."""
        if file_path.is_absolute():
            return file_path if file_path.exists() else None
            
        # Try paths in order:
        search_paths = [
            base_path / file_path,  # Direct relative path
            base_path / "attachments" / file_path.name,  # Attachments dir
            *[p / "attachments" / file_path.name for p in base_path.parents]  # Parent dirs
        ]
        
        for path in search_paths:
            if path.exists():
                return path
                
        return None

    def __init__(self, media_dir: Path, error_tolerance: bool = False):
        """Initialize the attachment processor.
        
        Args:
            media_dir: Directory for processed attachments
            error_tolerance: Whether to continue on non-critical errors
        """
        self.media_dir = media_dir
        self.error_tolerance = error_tolerance
        
        # Initialize converters
        self.converters = {
            AttachmentType.WORD: WordConverter(),
            AttachmentType.PDF: PDFConverter(),
            AttachmentType.POWERPOINT: PowerPointConverter(),
            AttachmentType.IMAGE: ImageConverter(),
        }
        
        # Create media directories
        for att_type in AttachmentType:
            (self.media_dir / att_type.value).mkdir(parents=True, exist_ok=True)

    async def process_attachment(self, file_path: Path) -> Optional[Attachment]:
        """Process an attachment file.
        
        Args:
            file_path: Path to attachment file
            
        Returns:
            Processed attachment or None if processing failed
            
        Raises:
            ProcessingError: If processing fails and error_tolerance is False
        """
        try:
            # Detect type
            att_type = await self._detect_type(file_path)
            
            # Generate unique name
            unique_name = await self._generate_unique_name(file_path)
            
            # Get target path
            target_path = self.media_dir / att_type.value / unique_name
            
            # Copy file
            await self._copy_file(file_path, target_path)
            
            # Get metadata
            metadata = await self._get_metadata(file_path, att_type)
            
            # Convert content if needed
            content = await self._convert_content(file_path, att_type)
            
            return Attachment(
                original_path=file_path,
                processed_path=target_path,
                type=att_type,
                size=file_path.stat().st_size,
                metadata=metadata,
                content=content
            )
            
        except Exception as e:
            msg = f"Failed to process attachment {file_path}: {str(e)}"
            if self.error_tolerance:
                logger.warning(msg)
                return None
            raise ProcessingError(msg, stage="attachment_processing")

    async def _detect_type(self, file_path: Path) -> AttachmentType:
        """Detect attachment type.
        
        Args:
            file_path: Path to file
            
        Returns:
            Detected attachment type
        """
        # Use python-magic to get MIME type
        mime_type = magic.from_file(str(file_path), mime=True)
        
        # Map MIME types to attachment types
        mime_map = {
            'application/pdf': AttachmentType.PDF,
            'application/msword': AttachmentType.WORD,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': AttachmentType.WORD,
            'application/vnd.ms-powerpoint': AttachmentType.POWERPOINT,
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': AttachmentType.POWERPOINT,
            'image/': AttachmentType.IMAGE
        }
        
        for mime_prefix, att_type in mime_map.items():
            if mime_type.startswith(mime_prefix):
                return att_type
                
        return AttachmentType.OTHER

    async def _generate_unique_name(self, file_path: Path) -> str:
        """Generate unique name for processed attachment.
        
        Args:
            file_path: Original file path
            
        Returns:
            Unique filename
        """
        # Get timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Calculate file hash
        async with aiofiles.open(file_path, 'rb') as f:
            content = await f.read()
            file_hash = hashlib.md5(content).hexdigest()[:8]
        
        # Combine parts
        return f"{timestamp}_{file_hash}_{file_path.name}"

    async def _copy_file(self, source: Path, target: Path) -> None:
        """Copy file using async operations.
        
        Args:
            source: Source file path
            target: Target file path
        """
        target.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(source, 'rb') as src, \
                   aiofiles.open(target, 'wb') as dst:
            while chunk := await src.read(8192):  # 8KB chunks
                await dst.write(chunk)

    async def _get_metadata(
        self,
        file_path: Path,
        att_type: AttachmentType
    ) -> Dict[str, Any]:
        """Get attachment metadata.
        
        Args:
            file_path: Path to file
            att_type: Attachment type
            
        Returns:
            Dictionary of metadata
        """
        metadata = {
            'filename': file_path.name,
            'size': file_path.stat().st_size,
            'created': datetime.fromtimestamp(file_path.stat().st_ctime),
            'modified': datetime.fromtimestamp(file_path.stat().st_mtime),
            'mime_type': magic.from_file(str(file_path), mime=True)
        }
        
        # Get type-specific metadata
        if att_type in self.converters:
            try:
                additional_meta = await self.converters[att_type].get_metadata(file_path)
                metadata.update(additional_meta)
            except Exception as e:
                logger.warning(
                    f"Failed to get {att_type.value} metadata",
                    error=str(e)
                )
                
        return metadata

    async def _convert_content(
        self,
        file_path: Path,
        att_type: AttachmentType
    ) -> Optional[str]:
        """Convert attachment content if needed.
        
        Args:
            file_path: Path to file
            att_type: Attachment type
            
        Returns:
            Converted content or None
        """
        if att_type in self.converters:
            try:
                return await self.converters[att_type].convert(file_path)
            except Exception as e:
                logger.warning(
                    f"Failed to convert {att_type.value} content",
                    error=str(e)
                )
        return None
