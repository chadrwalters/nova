"""Handler for consolidating markdown files and their attachments."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import hashlib
from datetime import datetime

from ....core.handlers.base import BaseHandler, HandlerResult
from ....core.errors import HandlerError
from ....core.utils.retry import async_retry
from ....core.handlers.document_handlers import DocumentHandler
from ....core.handlers.image_handlers import ImageHandler
from ....core.utils.reference_manager import ReferenceManager

class ConsolidateHandler(BaseHandler):
    """Handler for consolidating markdown files and their attachments."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize the consolidate handler.
        
        Args:
            config: Optional configuration overrides
        """
        super().__init__(config)
        
        # Initialize handlers
        self.document_handler = DocumentHandler(config)
        self.image_handler = ImageHandler(config)
        self.reference_manager = ReferenceManager(config)
        
        # Configure markers
        self.attachment_markers = self.get_option('attachment_markers', {
            'start': '--==ATTACHMENT_BLOCK: {filename}==--',
            'end': '--==ATTACHMENT_BLOCK_END==--'
        })
        
        # Set up hooks
        self.add_pre_process_hook(self._pre_process)
        self.add_post_process_hook(self._post_process)
        self.add_error_hook(self._on_error)
    
    async def _pre_process(self, file_path: Path, context: Dict[str, Any]) -> None:
        """Pre-process hook implementation."""
        self.metrics.record('start_time', datetime.now().timestamp())
        self.metrics.record('file_size', file_path.stat().st_size)
        if context.get('attachments'):
            self.metrics.record('attachment_count', len(context['attachments']))
    
    async def _post_process(self, result: HandlerResult) -> None:
        """Post-process hook implementation."""
        self.metrics.record('end_time', datetime.now().timestamp())
        self.metrics.record('content_length', len(result.content))
        self.metrics.record('metadata_count', len(result.metadata))
        self.metrics.record('error_count', len(result.errors))
        self.metrics.record('warning_count', len(result.warnings))
        self.metrics.record('processed_attachments', len(result.processed_attachments))
    
    async def _on_error(self, error: Exception, result: HandlerResult) -> None:
        """Error hook implementation."""
        self.metrics.record('error_type', error.__class__.__name__)
        self.metrics.record('error_message', str(error))
    
    def _get_cache_key(self, file_path: Path, attachments: List[Path]) -> str:
        """Generate cache key for a file and its attachments.
        
        Args:
            file_path: Path to the main file
            attachments: List of attachment paths
            
        Returns:
            Cache key string
        """
        content_hash = hashlib.sha256()
        content_hash.update(str(file_path).encode())
        content_hash.update(str(file_path.stat().st_mtime).encode())
        
        for attachment in sorted(attachments):
            content_hash.update(str(attachment).encode())
            content_hash.update(str(attachment.stat().st_mtime).encode())
        
        return content_hash.hexdigest()
    
    async def can_handle(self, file_path: Path, attachments: Optional[List[Path]] = None) -> bool:
        """Check if file can be consolidated.
        
        Args:
            file_path: Path to the file to check
            attachments: Optional list of attachments
            
        Returns:
            bool: True if file is markdown and has attachments
        """
        return (
            file_path.suffix.lower() in {'.md', '.markdown'} and
            attachments is not None and
            len(attachments) > 0 and
            await self.file_ops.path_exists(file_path)
        )
    
    async def _process_attachment(self, attachment: Path) -> Dict[str, Any]:
        """Process a single attachment.
        
        Args:
            attachment: Path to the attachment
            
        Returns:
            Dict containing processed content and metadata
        """
        try:
            # Determine handler based on file type
            if self.image_handler.can_handle(attachment):
                handler = self.image_handler
                self.metrics.record('attachment_type', 'image')
            elif self.document_handler.can_handle(attachment):
                handler = self.document_handler
                self.metrics.record('attachment_type', 'document')
            else:
                raise HandlerError(f"No handler available for {attachment}")
            
            # Process attachment
            result = await handler.process(attachment, {})
            
            # Update metrics
            self.metrics.record('attachment_size', attachment.stat().st_size)
            self.metrics.record('attachment_processing_time', result.processing_time)
            
            return {
                'content': result.content,
                'metadata': result.metadata,
                'type': handler.__class__.__name__
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process attachment {attachment}: {str(e)}")
            self.metrics.record('attachment_processing_error', 1)
            raise HandlerError(f"Failed to process attachment {attachment}: {str(e)}")
    
    @async_retry()
    async def process(
        self,
        file_path: Path,
        context: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Path]] = None
    ) -> HandlerResult:
        """Process file and its attachments.
        
        Args:
            file_path: Path to the main file
            context: Optional processing context
            attachments: Optional list of attachments
            
        Returns:
            HandlerResult containing consolidated content
        """
        result = HandlerResult()
        context = context or {}
        attachments = attachments or []
        
        try:
            # Check cache first
            cache_key = self._get_cache_key(file_path, attachments)
            
            if self._cache_enabled and cache_key in self._cache:
                self.metrics.record('cache_hits', 1)
                cached_result = self._cache[cache_key]
                result.content = cached_result['content']
                result.metadata = cached_result['metadata']
                result.processed_attachments = cached_result['processed_attachments']
            else:
                self.metrics.record('cache_misses', 1)
                
                # Read main file
                content = await self.file_ops.read_file(file_path)
                result.content = content
                result.processed_files.append(file_path)
                
                # Process each attachment
                for attachment in attachments:
                    try:
                        processed = await self._process_attachment(attachment)
                        
                        # Add attachment block
                        result.content += f"\n\n{self.attachment_markers['start'].format(filename=attachment.name)}\n"
                        result.content += processed['content']
                        result.content += f"\n{self.attachment_markers['end']}\n"
                        
                        # Update metadata and tracking
                        result.metadata[attachment.name] = processed['metadata']
                        result.processed_attachments.append(attachment)
                        
                    except Exception as e:
                        result.errors.append(f"Failed to process attachment {attachment}: {str(e)}")
                        self.metrics.record('attachment_error', 1)
                
                # Update references
                result.content = await self.reference_manager.update_references(
                    result.content,
                    result.processed_attachments
                )
                
                # Cache the result
                if self._cache_enabled:
                    self._cache[cache_key] = {
                        'content': result.content,
                        'metadata': result.metadata,
                        'processed_attachments': result.processed_attachments
                    }
            
            # Record final metrics
            self.metrics.record('total_content_size', len(result.content))
            self.metrics.record('total_attachments', len(result.processed_attachments))
            
        except Exception as e:
            result.errors.append(f"Consolidation failed: {str(e)}")
            self.metrics.record('consolidation_error', 1)
        
        return result
    
    def validate_output(self, result: HandlerResult) -> bool:
        """Validate processing results.
        
        Args:
            result: HandlerResult to validate
            
        Returns:
            bool: True if results are valid
        """
        if not super().validate_output(result):
            return False
        
        # Additional validation specific to this handler
        if not result.processed_attachments:
            self.logger.error("No attachments were processed")
            self.metrics.record('validation_error', 'no_attachments_processed')
            return False
        
        # Validate attachment blocks
        for attachment in result.processed_attachments:
            start_marker = self.attachment_markers['start'].format(filename=attachment.name)
            end_marker = self.attachment_markers['end']
            if start_marker not in result.content or end_marker not in result.content:
                self.logger.error(f"Missing attachment markers for {attachment.name}")
                self.metrics.record('validation_error', 'missing_markers')
                return False
        
        return True
    
    async def rollback(self, result: HandlerResult) -> None:
        """Rollback changes if processing fails.
        
        Args:
            result: HandlerResult to rollback
        """
        await super().rollback(result)
        
        # Additional cleanup specific to this handler
        try:
            # Clean up any temporary files created by handlers
            await self.document_handler.cleanup()
            await self.image_handler.cleanup()
            
            self.metrics.record('rollback_success', True)
            
        except Exception as e:
            self.logger.error(f"Error during rollback: {str(e)}")
            self.metrics.record('rollback_error', str(e))
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        await super().cleanup()
        
        # Additional cleanup specific to this handler
        try:
            # Clean up handlers
            await self.document_handler.cleanup()
            await self.image_handler.cleanup()
            
            self.metrics.record('cleanup_success', True)
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}") 