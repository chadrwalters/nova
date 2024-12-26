"""Handler for consolidating markdown files and their attachments."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import hashlib
from datetime import datetime
import json

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
        """Process file and its attachments."""
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
                
                # Read main file and extract metadata
                content = await self.file_ops.read_file(file_path)
                metadata = self._extract_metadata(content)
                content = self._remove_metadata_comment(content)
                
                # Initialize consolidated metadata
                consolidated_metadata = await self._initialize_consolidated_metadata(metadata, file_path)
                
                # Process content based on document hierarchy and relationships
                processed_content = await self._process_content_blocks(
                    metadata, 
                    consolidated_metadata,
                    context
                )
                
                # Process attachments with relationship context
                processed_content = await self._process_attachments_with_context(
                    processed_content,
                    attachments,
                    metadata,
                    consolidated_metadata,
                    result
                )
                
                # Update all reference types
                processed_content = await self._update_all_references(
                    processed_content,
                    metadata,
                    consolidated_metadata,
                    result.processed_attachments
                )
                
                # Add consolidated metadata as comment
                result.content = f"<!-- {json.dumps(consolidated_metadata, default=serialize_date)} -->\n\n{processed_content}"
                result.metadata = consolidated_metadata
                result.processed_files.append(file_path)
                
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

    async def _initialize_consolidated_metadata(
        self, 
        metadata: Dict[str, Any],
        file_path: Path
    ) -> Dict[str, Any]:
        """Initialize consolidated metadata with hierarchy information."""
        consolidated_metadata = {
            'document': metadata.get('document', {}),
            'structure': metadata.get('structure', {}),
            'relationships': metadata.get('relationships', {}),
            'assembly': metadata.get('assembly', {}),
            'content_markers': metadata.get('content_markers', {}),
            'consolidated': {
                'timestamp': datetime.now().isoformat(),
                'source_files': [str(file_path)],
                'attachment_files': [],
                'content_blocks': {
                    'summary': [],
                    'raw_notes': [],
                    'attachments': []
                },
                'hierarchy': {
                    'root_document': metadata.get('structure', {}).get('root_document', True),
                    'parent_document': metadata.get('structure', {}).get('parent_document'),
                    'child_documents': [],
                    'group_id': metadata.get('assembly', {}).get('group'),
                    'sequence_number': metadata.get('structure', {}).get('sequence_number', 1)
                },
                'processing': {
                    'merge_conflicts': [],
                    'unresolved_references': [],
                    'missing_dependencies': []
                }
            }
        }
        return consolidated_metadata

    async def _process_content_blocks(
        self,
        metadata: Dict[str, Any],
        consolidated_metadata: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Process content blocks respecting hierarchy and merge rules."""
        processed_blocks = []
        
        # Get merge priority and group info
        merge_priority = metadata.get('assembly', {}).get('merge_priority', 50)
        group_id = metadata.get('assembly', {}).get('group')
        
        # Process blocks by type, respecting priority
        block_types = ['summary', 'raw_notes', 'attachments']
        for block_type in block_types:
            blocks = metadata.get('content_markers', {}).get(f'{block_type}_blocks', [])
            
            # Sort blocks by priority if in a group
            if group_id:
                blocks = sorted(
                    blocks,
                    key=lambda b: (merge_priority, b.get('start_line', 0))
                )
            
            for block in blocks:
                # Check for conflicts
                if self._has_content_conflict(block, consolidated_metadata):
                    consolidated_metadata['consolidated']['processing']['merge_conflicts'].append({
                        'block_type': block_type,
                        'content': block.get('content', []),
                        'source_file': str(metadata['document']['file']),
                        'start_line': block.get('start_line')
                    })
                    continue
                
                # Add block content
                if isinstance(block.get('content'), list):
                    processed_blocks.extend(block['content'])
                else:
                    processed_blocks.append(block.get('content', ''))
                
                # Track in consolidated metadata
                consolidated_metadata['consolidated']['content_blocks'][block_type].append({
                    'source_file': str(metadata['document']['file']),
                    'start_line': block.get('start_line'),
                    'merge_priority': merge_priority,
                    'group_id': group_id,
                    'content': '\n'.join(block['content']) if isinstance(block.get('content'), list) else block.get('content', '')
                })
                
            # Add separator between block types
            if blocks:
                processed_blocks.append('')
        
        return '\n'.join(processed_blocks)

    def _has_content_conflict(
        self,
        block: Dict[str, Any],
        consolidated_metadata: Dict[str, Any]
    ) -> bool:
        """Check for content conflicts in consolidated blocks."""
        block_content = '\n'.join(block['content']) if isinstance(block.get('content'), list) else block.get('content', '')
        
        # Check all block types for conflicts
        for block_type in consolidated_metadata['consolidated']['content_blocks']:
            for existing_block in consolidated_metadata['consolidated']['content_blocks'][block_type]:
                if block_content == existing_block['content']:
                    return True
                
        return False

    async def _update_all_references(
        self,
        content: str,
        metadata: Dict[str, Any],
        consolidated_metadata: Dict[str, Any],
        processed_attachments: List[Path]
    ) -> str:
        """Update all reference types in content."""
        try:
            # Update attachment references
            content = await self.reference_manager.update_references(
                content,
                processed_attachments
            )
            
            # Process other reference types from metadata
            references = metadata.get('relationships', {}).get('references', [])
            for ref in references:
                if ref['type'] == 'link':
                    # Update internal document links
                    content = await self._update_document_link(
                        content,
                        ref,
                        consolidated_metadata
                    )
                elif ref['type'] == 'image':
                    # Update image references
                    content = await self._update_image_reference(
                        content,
                        ref,
                        consolidated_metadata
                    )
            
            # Track unresolved references
            unresolved = await self._find_unresolved_references(content)
            if unresolved:
                consolidated_metadata['consolidated']['processing']['unresolved_references'].extend(unresolved)
            
            return content
            
        except Exception as e:
            self.logger.error(f"Error updating references: {str(e)}")
            return content

    async def _update_document_link(
        self,
        content: str,
        ref: Dict[str, str],
        consolidated_metadata: Dict[str, Any]
    ) -> str:
        """Update internal document link references."""
        try:
            # Implementation for updating document links
            return content
        except Exception as e:
            self.logger.error(f"Error updating document link: {str(e)}")
            return content

    async def _update_image_reference(
        self,
        content: str,
        ref: Dict[str, str],
        consolidated_metadata: Dict[str, Any]
    ) -> str:
        """Update image references."""
        try:
            # Implementation for updating image references
            return content
        except Exception as e:
            self.logger.error(f"Error updating image reference: {str(e)}")
            return content

    async def _find_unresolved_references(self, content: str) -> List[Dict[str, Any]]:
        """Find any unresolved references in content."""
        unresolved = []
        # Implementation for finding unresolved references
        return unresolved

    async def _process_attachments_with_context(
        self,
        content: str,
        attachments: List[Path],
        metadata: Dict[str, Any],
        consolidated_metadata: Dict[str, Any],
        result: HandlerResult
    ) -> str:
        """Process attachments with relationship context."""
        processed_lines = []
        
        for attachment in attachments:
            try:
                processed = await self._process_attachment(attachment)
                
                # Add attachment block with metadata
                start_marker = self.attachment_markers['start'].format(filename=attachment.name)
                end_marker = self.attachment_markers['end']
                
                attachment_content = [
                    start_marker,
                    processed['content'],
                    end_marker
                ]
                processed_lines.extend(attachment_content)
                
                # Update metadata with relationship context
                attachment_metadata = {
                    'filename': attachment.name,
                    'type': processed['type'],
                    'metadata': processed['metadata'],
                    'relationships': self._extract_attachment_relationships(
                        attachment,
                        metadata
                    )
                }
                
                consolidated_metadata['consolidated']['attachment_files'].append(str(attachment))
                consolidated_metadata['consolidated']['content_blocks']['attachments'].append(attachment_metadata)
                
                result.processed_attachments.append(attachment)
                
            except Exception as e:
                result.errors.append(f"Failed to process attachment {attachment}: {str(e)}")
                self.metrics.record('attachment_error', 1)
        
        return content + '\n' + '\n'.join(processed_lines) if processed_lines else content

    def _extract_attachment_relationships(
        self,
        attachment: Path,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract relationship information for an attachment."""
        relationships = {
            'referenced_by': [],
            'depends_on': [],
            'group_context': metadata.get('assembly', {}).get('group')
        }
        
        # Find references to this attachment
        for ref in metadata.get('relationships', {}).get('references', []):
            if attachment.name in ref.get('url', ''):
                relationships['referenced_by'].append({
                    'type': ref['type'],
                    'context': ref.get('text') or ref.get('alt')
                })
        
        return relationships
    
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
    
    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from content HTML comment."""
        try:
            # Find metadata comment
            start = content.find('<!--')
            end = content.find('-->', start)
            if start == -1 or end == -1:
                return {}
                
            # Parse metadata JSON
            metadata_str = content[start + 4:end].strip()
            return json.loads(metadata_str)
            
        except Exception as e:
            self.logger.error(f"Error extracting metadata: {str(e)}")
            return {}
            
    def _remove_metadata_comment(self, content: str) -> str:
        """Remove metadata HTML comment from content."""
        try:
            # Find metadata comment
            start = content.find('<!--')
            end = content.find('-->', start)
            if start == -1 or end == -1:
                return content
                
            # Remove comment and any following whitespace
            return content[end + 3:].lstrip()
            
        except Exception as e:
            self.logger.error(f"Error removing metadata comment: {str(e)}")
            return content 