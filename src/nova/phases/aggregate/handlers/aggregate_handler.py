"""Handler for aggregating markdown files."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
import hashlib
from datetime import datetime

from ....core.handlers.base import BaseHandler, HandlerResult
from ....core.errors import HandlerError
from ....core.utils.retry import async_retry

class AggregateHandler(BaseHandler):
    """Handles aggregation of markdown files and classified content."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the aggregation handler.
        
        Args:
            config: Optional configuration overrides
        """
        super().__init__(config)
        
        # Configure markers
        self.markers = self.get_option('section_markers', {
            'start': '<!-- START_FILE: {filename} -->',
            'end': '<!-- END_FILE: {filename} -->',
            'separator': '\n---\n'
        })
        
        # Initialize tracking
        self.processed_files: Set[Path] = set()
        
        # Set up hooks
        self.add_pre_process_hook(self._pre_process)
        self.add_post_process_hook(self._post_process)
        self.add_error_hook(self._on_error)
    
    async def _pre_process(self, file_path: Path, context: Dict[str, Any]) -> None:
        """Pre-process hook implementation."""
        self.metrics.record('start_time', datetime.now().timestamp())
        if await self.file_ops.is_directory(file_path):
            self.metrics.record('input_type', 'directory')
            file_count = 0
            async for _ in self.file_ops.scan_directory(file_path, recursive=True):
                file_count += 1
            self.metrics.record('total_files', file_count)
        else:
            self.metrics.record('input_type', 'file')
            self.metrics.record('total_files', 1)
    
    async def _post_process(self, result: HandlerResult) -> None:
        """Post-process hook implementation."""
        self.metrics.record('end_time', datetime.now().timestamp())
        self.metrics.record('processed_files', len(result.processed_files))
        self.metrics.record('content_length', len(result.content))
        self.metrics.record('metadata_count', len(result.metadata))
        self.metrics.record('error_count', len(result.errors))
        self.metrics.record('warning_count', len(result.warnings))
    
    async def _on_error(self, error: Exception, result: HandlerResult) -> None:
        """Error hook implementation."""
        self.metrics.record('error_type', error.__class__.__name__)
        self.metrics.record('error_message', str(error))
    
    def _get_cache_key(self, file_path: Path) -> str:
        """Generate cache key for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Cache key string
        """
        content_hash = hashlib.sha256()
        content_hash.update(str(file_path).encode())
        content_hash.update(str(file_path.stat().st_mtime).encode())
        return content_hash.hexdigest()
    
    async def can_handle(self, file_path: Path, attachments: Optional[List[Path]] = None) -> bool:
        """Check if file can be aggregated.
        
        Args:
            file_path: Path to the file to check
            attachments: Optional list of attachments (not used)
            
        Returns:
            bool: True if file is markdown or a directory containing markdown files
        """
        if await self.file_ops.is_directory(file_path):
            # Check if directory contains markdown files
            has_markdown = False
            async for entry in self.file_ops.scan_directory(file_path, recursive=True):
                if entry.suffix.lower() in {'.md', '.markdown'}:
                    has_markdown = True
                    break
            return has_markdown
        return file_path.suffix.lower() in {'.md', '.markdown'}
    
    async def _process_file(self, file_path: Path) -> Dict[str, Any]:
        """Process a single markdown file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dict containing processed content and metadata
        """
        try:
            # Check cache first
            cache_key = self._get_cache_key(file_path)
            
            if self._cache_enabled and cache_key in self._cache:
                self.metrics.record('cache_hits', 1)
                return self._cache[cache_key]
            
            self.metrics.record('cache_misses', 1)
            
            # Read and process file
            content = await self.file_ops.read_file(file_path)
            
            # Add section markers
            processed = {
                'content': (
                    f"{self.markers['start'].format(filename=file_path.name)}\n"
                    f"{content}\n"
                    f"{self.markers['end'].format(filename=file_path.name)}"
                ),
                'metadata': {
                    'filename': file_path.name,
                    'modified': file_path.stat().st_mtime,
                    'size': file_path.stat().st_size
                }
            }
            
            # Cache the result
            if self._cache_enabled:
                self._cache[cache_key] = processed
            
            return processed
            
        except Exception as e:
            self.logger.error(f"Failed to process {file_path}: {str(e)}")
            self.metrics.record('file_processing_error', 1)
            raise HandlerError(f"Failed to process {file_path}: {str(e)}")
    
    @async_retry()
    async def process(
        self,
        file_path: Path,
        context: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Path]] = None
    ) -> HandlerResult:
        """Process file(s) and aggregate content.
        
        Args:
            file_path: Path to file or directory to process
            context: Optional processing context
            attachments: Optional list of attachments (not used)
            
        Returns:
            HandlerResult containing aggregated content
        """
        result = HandlerResult()
        context = context or {}
        
        try:
            # Get list of files to process
            files_to_process: List[Path] = []
            
            if await self.file_ops.is_directory(file_path):
                async for entry in self.file_ops.scan_directory(file_path, recursive=True):
                    if entry.suffix.lower() in {'.md', '.markdown'}:
                        files_to_process.append(entry)
            else:
                files_to_process = [file_path]
            
            # Sort files by modification time if requested
            if context.get('sort_by_date', True):
                files_to_process.sort(key=lambda f: f.stat().st_mtime)
                self.metrics.record('sorted_files', True)
            
            # Process each file
            sections = []
            for file_path in files_to_process:
                if file_path not in self.processed_files:
                    processed = await self._process_file(file_path)
                    sections.append(processed['content'])
                    result.metadata[file_path.name] = processed['metadata']
                    result.processed_files.append(file_path)
                    self.processed_files.add(file_path)
                    
                    # Update metrics
                    self.metrics.record('file_size', processed['metadata']['size'])
                    self.metrics.record('section_count', len(sections))
            
            # Combine sections
            result.content = self.markers['separator'].join(sections)
            
            # Update file map
            for i, file_path in enumerate(result.processed_files):
                result.file_map[file_path.name] = i
            
            # Record final metrics
            self.metrics.record('total_content_size', len(result.content))
            self.metrics.record('total_sections', len(sections))
            self.metrics.record('unique_files', len(self.processed_files))
            
        except Exception as e:
            result.errors.append(f"Aggregation failed: {str(e)}")
            self.metrics.record('aggregation_error', 1)
        
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
        if not result.processed_files:
            self.logger.error("No files were processed")
            self.metrics.record('validation_error', 'no_files_processed')
            return False
        
        if not result.file_map:
            self.logger.error("File map is empty")
            self.metrics.record('validation_error', 'empty_file_map')
            return False
        
        # Validate section markers
        for file_path in result.processed_files:
            start_marker = self.markers['start'].format(filename=file_path.name)
            end_marker = self.markers['end'].format(filename=file_path.name)
            if start_marker not in result.content or end_marker not in result.content:
                self.logger.error(f"Missing section markers for {file_path.name}")
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
            # Remove processed files from tracking
            for file_path in result.processed_files:
                self.processed_files.discard(file_path)
            
            self.metrics.record('rollback_success', True)
            
        except Exception as e:
            self.logger.error(f"Error during rollback: {str(e)}")
            self.metrics.record('rollback_error', str(e))
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        await super().cleanup()
        
        # Additional cleanup specific to this handler
        try:
            # Clear processed files tracking
            self.processed_files.clear()
            
            self.metrics.record('cleanup_success', True)
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}") 