"""Unified handler for classification and aggregation."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import aiofiles
import hashlib
from datetime import datetime

from ....core.handlers.base import BaseHandler, HandlerResult
from ....core.errors import HandlerError
from ....core.utils.retry import async_retry

class UnifiedHandler(BaseHandler):
    """Unified handler for classification and aggregation of markdown content.
    
    This handler combines the functionality of ClassificationHandler and AggregationHandler
    into a single, more efficient implementation that can handle both individual file
    classification and multi-file aggregation.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the unified handler.
        
        Args:
            config: Optional configuration overrides
        """
        super().__init__(config)
        
        # Configure paths
        self.output_dir = Path(self.get_option('output_dir', '.'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure processing options
        self.sort_by_date = self.get_option('sort_by_date', True)
        self.preserve_headers = self.get_option('preserve_headers', True)
        self.section_markers = self.get_option('section_markers', {
            'start': "<!-- START_FILE: {filename} -->",
            'end': "<!-- END_FILE: {filename} -->",
            'separator': "\n---\n"
        })
        
        # Set up hooks
        self.add_pre_process_hook(self._pre_process)
        self.add_post_process_hook(self._post_process)
        self.add_error_hook(self._on_error)
    
    async def _pre_process(self, file_path: Path, context: Dict[str, Any]) -> None:
        """Pre-process hook implementation."""
        self.metrics.record('file_count', 1 if not isinstance(file_path, list) else len(file_path))
        self.metrics.record('start_time', datetime.now().timestamp())
    
    async def _post_process(self, result: HandlerResult) -> None:
        """Post-process hook implementation."""
        self.metrics.record('end_time', datetime.now().timestamp())
        self.metrics.record('content_length', len(result.content))
        self.metrics.record('metadata_count', len(result.metadata))
        self.metrics.record('error_count', len(result.errors))
        self.metrics.record('warning_count', len(result.warnings))
    
    async def _on_error(self, error: Exception, result: HandlerResult) -> None:
        """Error hook implementation."""
        self.metrics.record('error_type', error.__class__.__name__)
        self.metrics.record('error_message', str(error))
    
    def can_handle(
        self,
        file_path: Path,
        attachments: Optional[List[Path]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if file(s) can be processed.
        
        Args:
            file_path: Path to the main file
            attachments: Optional list of attachments
            context: Optional processing context
            
        Returns:
            bool: True if files can be processed
        """
        # Handle both single files and multiple files
        if isinstance(file_path, list):
            return all(
                f.suffix.lower() in {'.md', '.markdown'}
                for f in file_path
            )
        else:
            return (
                file_path.suffix.lower() in {'.md', '.markdown'} and
                (file_path.with_suffix('.json').exists() or context.get('skip_metadata', False))
            )
    
    def _get_cache_key(self, file_path: Path, metadata: Dict[str, Any]) -> str:
        """Generate cache key for a file.
        
        Args:
            file_path: Path to the file
            metadata: File metadata
            
        Returns:
            Cache key string
        """
        content_hash = hashlib.sha256()
        content_hash.update(str(file_path).encode())
        content_hash.update(str(metadata).encode())
        content_hash.update(str(file_path.stat().st_mtime).encode())
        return content_hash.hexdigest()
    
    async def _load_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Load metadata for a file.
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            Dict containing metadata
        """
        try:
            metadata_path = file_path.with_suffix('.json')
            if await self.file_ops.path_exists(metadata_path):
                content = await self.file_ops.read_file(metadata_path)
                return json.loads(content)
        except Exception as e:
            self.logger.warning(f"Failed to load metadata for {file_path}: {e}")
            self.metrics.record('metadata_load_error', 1)
        return {}
    
    @async_retry()
    async def _classify_content(
        self,
        content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Classify markdown content.
        
        Args:
            content: Markdown content to classify
            metadata: Associated metadata
            
        Returns:
            Dict containing classification results
        """
        # Implement classification logic here
        # This would use the same logic as the original ClassificationHandler
        pass
    
    @async_retry()
    async def _aggregate_files(
        self,
        files: List[Path],
        context: Dict[str, Any]
    ) -> HandlerResult:
        """Aggregate multiple markdown files.
        
        Args:
            files: List of files to aggregate
            context: Processing context
            
        Returns:
            HandlerResult containing aggregated content
        """
        result = HandlerResult()
        
        try:
            # Sort files if needed
            if self.sort_by_date:
                files.sort(key=lambda f: f.stat().st_mtime)
                self.metrics.record('sorted_files', True)
            
            # Process each file
            sections = []
            for file_path in files:
                # Check cache first
                metadata = await self._load_metadata(file_path)
                cache_key = self._get_cache_key(file_path, metadata)
                
                if self._cache_enabled and cache_key in self._cache:
                    self.metrics.record('cache_hits', 1)
                    section = self._cache[cache_key]
                else:
                    self.metrics.record('cache_misses', 1)
                    content = await self.file_ops.read_file(file_path)
                    
                    # Add section markers
                    section = (
                        f"{self.section_markers['start'].format(filename=file_path.name)}\n"
                        f"{content}\n"
                        f"{self.section_markers['end'].format(filename=file_path.name)}"
                    )
                    
                    # Cache the result
                    if self._cache_enabled:
                        self._cache[cache_key] = section
                
                sections.append(section)
                result.processed_files.append(file_path)
                result.file_map[file_path.name] = len(sections) - 1
                result.metadata[file_path.name] = metadata
            
            # Combine sections
            result.content = self.section_markers['separator'].join(sections)
            
            # Record metrics
            self.metrics.record('files_processed', len(files))
            self.metrics.record('total_sections', len(sections))
            self.metrics.record('content_size', len(result.content))
            
        except Exception as e:
            result.errors.append(f"Failed to aggregate files: {str(e)}")
            self.metrics.record('aggregation_error', 1)
        
        return result
    
    async def process(
        self,
        file_path: Path,
        context: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Path]] = None
    ) -> HandlerResult:
        """Process file(s) based on context.
        
        Args:
            file_path: Path to file(s) to process
            context: Processing context
            attachments: Optional list of attachments
            
        Returns:
            HandlerResult containing processing results
        """
        context = context or {}
        result = HandlerResult()
        
        try:
            # Handle multiple files (aggregation)
            if isinstance(file_path, list):
                self.metrics.record('operation_type', 'aggregation')
                return await self._aggregate_files(file_path, context)
            
            # Handle single file (classification)
            self.metrics.record('operation_type', 'classification')
            
            # Check cache first
            metadata = await self._load_metadata(file_path)
            cache_key = self._get_cache_key(file_path, metadata)
            
            if self._cache_enabled and cache_key in self._cache:
                self.metrics.record('cache_hits', 1)
                cached_result = self._cache[cache_key]
                result.content = cached_result['content']
                result.metadata = cached_result['metadata']
            else:
                self.metrics.record('cache_misses', 1)
                content = await self.file_ops.read_file(file_path)
                
                # Classify content
                classification = await self._classify_content(content, metadata)
                
                # Update result
                result.content = content
                result.metadata = {**metadata, **classification}
                
                # Cache the result
                if self._cache_enabled:
                    self._cache[cache_key] = {
                        'content': result.content,
                        'metadata': result.metadata
                    }
            
            result.processed_files.append(file_path)
            if attachments:
                result.processed_attachments.extend(attachments)
            
            # Record metrics
            self.metrics.record('content_size', len(result.content))
            self.metrics.record('metadata_size', len(result.metadata))
            
        except Exception as e:
            result.errors.append(f"Processing failed: {str(e)}")
            self.metrics.record('processing_error', 1)
        
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
        if isinstance(result.content, str) and not result.content.strip():
            self.logger.error("Content cannot be empty")
            self.metrics.record('validation_error', 'empty_content')
            return False
        
        # Validate metadata
        if not result.metadata:
            self.logger.warning("No metadata present in result")
            self.metrics.record('validation_warning', 'no_metadata')
        
        return True
    
    async def rollback(self, result: HandlerResult) -> None:
        """Rollback changes if processing fails.
        
        Args:
            result: HandlerResult to rollback
        """
        await super().rollback(result)
        
        # Additional cleanup specific to this handler
        try:
            # Clean up any temporary files
            for file_path in result.processed_files:
                temp_path = self.output_dir / f"{file_path.stem}_temp{file_path.suffix}"
                if await self.file_ops.path_exists(temp_path):
                    await self.file_ops.delete_file(temp_path)
            
            self.metrics.record('rollback_success', True)
            
        except Exception as e:
            self.logger.error(f"Error during rollback: {str(e)}")
            self.metrics.record('rollback_error', str(e))
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        await super().cleanup()
        
        # Additional cleanup specific to this handler
        try:
            # Clear any temporary files in output directory
            temp_files = await self.file_ops.list_files(self.output_dir, pattern="*_temp.*")
            for temp_file in temp_files:
                await self.file_ops.delete_file(temp_file)
            
            self.metrics.record('cleanup_success', True)
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
            self.metrics.record('cleanup_error', str(e)) 