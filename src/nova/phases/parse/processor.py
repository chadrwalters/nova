"""Markdown processor for Nova document processor."""

from pathlib import Path
from typing import Dict, Any, Optional, List
import os
import shutil
import mimetypes
import json

from ...core.config import ProcessorConfig, PipelineConfig
from ...core.logging import get_logger
from ...core.errors import ProcessorError
from ...core.file_ops import FileOperationsManager
from ...core.pipeline.base import BaseProcessor
from ...core.handlers.document_handlers import DocumentHandler
from ...core.handlers.image_handlers import ImageHandler
from ...core.handlers.office_handlers import OfficeHandler

logger = get_logger(__name__)

class MarkdownProcessor(BaseProcessor):
    """Processor for markdown files."""
    
    def __init__(self, processor_config: ProcessorConfig, pipeline_config: PipelineConfig):
        """Initialize markdown processor.
        
        Args:
            processor_config: Processor configuration
            pipeline_config: Pipeline configuration
        """
        logger.debug(f"Creating markdown processor with config: {processor_config}")
        super().__init__(processor_config, pipeline_config)
        self.file_ops = FileOperationsManager()
        
        # Initialize handlers from both component and phase configurations
        self.handlers = []
        
        # Initialize component handlers
        if processor_config.components:
            # Get component configurations
            markdown_config = processor_config.components.get('markdown_processor', {})
            image_config = processor_config.components.get('image_processor', {})
            office_config = processor_config.components.get('office_processor', {})
            
            # Initialize markdown handlers
            if markdown_config and markdown_config.handlers:
                handler_configs = {h.type: h for h in markdown_config.handlers}
                
                # Initialize MarkitdownHandler if configured
                if 'MarkitdownHandler' in handler_configs:
                    from .handlers.markdown.markdown_handler import MarkitdownHandler
                    handler = MarkitdownHandler(handler_configs['MarkitdownHandler'])
                    self.handlers.append(handler)
                    logger.info("Initialized MarkitdownHandler")
                
                # Initialize ConsolidationHandler if configured
                if 'ConsolidationHandler' in handler_configs:
                    from .handlers.markdown.consolidation_handler import ConsolidationHandler
                    handler = ConsolidationHandler(handler_configs['ConsolidationHandler'])
                    self.handlers.append(handler)
                    logger.info("Initialized ConsolidationHandler")
            
            # Initialize specialized handlers with their configs
            self.document_handler = DocumentHandler(processor_config)
            self.image_handler = ImageHandler(image_config)
            self.office_handler = OfficeHandler(office_config)
            logger.info("Initialized specialized handlers")
        
        # Initialize phase handlers
        if processor_config.handlers:
            for handler_config in processor_config.handlers:
                if handler_config.type == 'UnifiedHandler':
                    from .handlers.unified import UnifiedHandler
                    handler = UnifiedHandler(handler_config.options or {})
                    self.handlers.append(handler)
                    logger.info("Initialized UnifiedHandler")
        
        logger.info(f"Initialized {len(self.handlers)} handlers for markdown processing")
        
    async def setup(self) -> None:
        """Set up processor."""
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create required subdirectories
        for subdir in ['images', 'documents', 'office']:
            (self.output_dir / subdir).mkdir(parents=True, exist_ok=True)
        
    async def process(self) -> bool:
        """Process markdown files.
        
        Returns:
            True if processing completed successfully, False otherwise
        """
        try:
            # Get input files
            input_files = list(Path(self.pipeline_config.input_dir).glob('**/*.md'))
            if not input_files:
                logger.warning("No markdown files found to process")
                return True
                
            logger.info(f"Found {len(input_files)} markdown files to process")
            
            # Process each file
            for input_file in input_files:
                try:
                    logger.info(f"Processing {input_file}")
                    await self._process_file(input_file)
                except Exception as e:
                    logger.error(f"Failed to process {input_file}: {str(e)}")
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"Error in markdown processor: {str(e)}")
            return False
            
    async def _process_file(self, input_file: Path) -> None:
        """Process a single markdown file.
        
        Args:
            input_file: Path to input file
            
        Raises:
            ProcessorError: If processing fails
        """
        try:
            # Read input file
            content = await self.file_ops.read_file(input_file)
            
            # Create output path preserving directory structure
            rel_path = input_file.relative_to(self.pipeline_config.input_dir)
            output_file = self.output_dir / rel_path
            
            # Create parent directories
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Check for attachments directory
            attachments_dir = input_file.parent / input_file.stem
            output_attachments_dir = None
            attachment_manifest = {
                'images': [],
                'documents': [],
                'office': [],
                'other': []
            }
            
            if attachments_dir.exists() and attachments_dir.is_dir():
                # Create corresponding output directory
                output_attachments_dir = output_file.parent / output_file.stem
                output_attachments_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Found attachments directory: {attachments_dir}")
                logger.info(f"Created output attachments directory: {output_attachments_dir}")
                
                # Process each attachment
                for attachment in attachments_dir.iterdir():
                    if attachment.is_file():
                        try:
                            # Determine file type
                            mime_type, _ = mimetypes.guess_type(attachment)
                            
                            if mime_type:
                                # Process images
                                if mime_type.startswith('image/'):
                                    # Copy to images directory
                                    image_dir = self.output_dir / 'images' / output_file.stem
                                    image_dir.mkdir(parents=True, exist_ok=True)
                                    dest_path = image_dir / attachment.name
                                    
                                    if not dest_path.exists():
                                        shutil.copy2(attachment, dest_path)
                                        
                                    # Add to manifest
                                    attachment_manifest['images'].append({
                                        'original_path': str(attachment),
                                        'processed_path': str(dest_path),
                                        'mime_type': mime_type,
                                        'size': os.path.getsize(attachment)
                                    })
                                    logger.info(f"Processed image: {attachment.name}")
                                
                                # Process office documents
                                elif mime_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                                                'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                                'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation']:
                                    # Copy to office directory
                                    office_dir = self.output_dir / 'office' / output_file.stem
                                    office_dir.mkdir(parents=True, exist_ok=True)
                                    dest_path = office_dir / attachment.name
                                    
                                    if not dest_path.exists():
                                        shutil.copy2(attachment, dest_path)
                                        
                                    # Add to manifest
                                    attachment_manifest['office'].append({
                                        'original_path': str(attachment),
                                        'processed_path': str(dest_path),
                                        'mime_type': mime_type,
                                        'size': os.path.getsize(attachment)
                                    })
                                    logger.info(f"Processed office document: {attachment.name}")
                                
                                # Process other documents (PDF, HTML, etc.)
                                elif mime_type in ['application/pdf', 'text/html', 'text/csv']:
                                    # Copy to documents directory
                                    doc_dir = self.output_dir / 'documents' / output_file.stem
                                    doc_dir.mkdir(parents=True, exist_ok=True)
                                    dest_path = doc_dir / attachment.name
                                    
                                    if not dest_path.exists():
                                        shutil.copy2(attachment, dest_path)
                                        
                                    # Add to manifest
                                    attachment_manifest['documents'].append({
                                        'original_path': str(attachment),
                                        'processed_path': str(dest_path),
                                        'mime_type': mime_type,
                                        'size': os.path.getsize(attachment)
                                    })
                                    logger.info(f"Processed document: {attachment.name}")
                                
                                # Copy other files as-is
                                else:
                                    dest_path = output_attachments_dir / attachment.name
                                    if not dest_path.exists():
                                        shutil.copy2(attachment, dest_path)
                                        
                                    # Add to manifest
                                    attachment_manifest['other'].append({
                                        'original_path': str(attachment),
                                        'processed_path': str(dest_path),
                                        'mime_type': mime_type,
                                        'size': os.path.getsize(attachment)
                                    })
                                    logger.info(f"Copied other file: {attachment.name}")
                            
                        except Exception as e:
                            logger.error(f"Failed to process attachment {attachment}: {str(e)}")
                            # Copy original file as fallback
                            dest_path = output_attachments_dir / attachment.name
                            if not dest_path.exists():
                                shutil.copy2(attachment, dest_path)
                                attachment_manifest['other'].append({
                                    'original_path': str(attachment),
                                    'processed_path': str(dest_path),
                                    'error': str(e)
                                })
                
                # Write attachment manifest
                manifest_path = output_attachments_dir / 'attachments.json'
                with open(manifest_path, 'w') as f:
                    json.dump(attachment_manifest, f, indent=2)
                logger.info(f"Wrote attachment manifest to {manifest_path}")
            
            # Write processed content
            with open(output_file, 'w') as f:
                f.write(content)
            logger.info(f"Wrote processed content to {output_file}")
            
        except Exception as e:
            raise ProcessorError(f"Failed to process file {input_file}: {str(e)}") 