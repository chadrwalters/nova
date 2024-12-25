"""Base handler classes for Nova document processor."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Set, Callable, Awaitable
import logging
import asyncio
from dataclasses import dataclass, field
from datetime import datetime

from ..logging import LoggerMixin
from ..errors import HandlerError, ConfigurationError
from ..config.base import HandlerConfig
from ..utils.file_ops import FileOperationsManager
from ..utils.retry import async_retry
from ..utils.metrics import MetricsTracker

@dataclass
class HandlerResult:
    """Result from handler processing."""
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    processed_files: List[Path] = field(default_factory=list)
    processed_attachments: List[Path] = field(default_factory=list)
    file_map: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metrics: Dict[str, Any] = field(default_factory=dict)

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)

    def add_metric(self, key: str, value: Any) -> None:
        """Add a metric."""
        self.metrics[key] = value

    def merge(self, other: 'HandlerResult') -> None:
        """Merge another result into this one."""
        self.content += other.content
        self.metadata.update(other.metadata)
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.processed_files.extend(other.processed_files)
        self.processed_attachments.extend(other.processed_attachments)
        self.file_map.update(other.file_map)
        self.metrics.update(other.metrics)

class BaseHandler(ABC, LoggerMixin):
    """Unified base class for all handlers.
    
    This class combines functionality from all phase-specific handlers into a single,
    consistent interface. It provides common utilities and enforces a standard
    contract for all handlers to follow.
    
    Features:
    - Unified configuration handling
    - Standardized file operations
    - Built-in retry mechanism
    - Metrics tracking
    - Resource cleanup
    - Async support
    - Error handling and recovery
    - Progress tracking
    - Event hooks
    """
    
    def __init__(self, config: Optional[Union[Dict[str, Any], HandlerConfig]] = None):
        """Initialize the handler.
        
        Args:
            config: Handler configuration, either as dict or HandlerConfig
        """
        super().__init__()
        self.config = config if isinstance(config, HandlerConfig) else HandlerConfig(**config) if config else HandlerConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize managers and utilities
        self.file_ops = FileOperationsManager()
        self.metrics = MetricsTracker(self.__class__.__name__)
        
        # Initialize state
        self.stats = {
            'processed': 0,
            'errors': 0,
            'warnings': 0,
            'retries': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Set up hooks
        self._pre_process_hooks: List[Callable[[Path, Dict[str, Any]], Awaitable[None]]] = []
        self._post_process_hooks: List[Callable[[HandlerResult], Awaitable[None]]] = []
        self._error_hooks: List[Callable[[Exception, HandlerResult], Awaitable[None]]] = []
        
        # Set up caching
        self._cache: Dict[str, Any] = {}
        self._cache_enabled = self.config.options.get('cache_enabled', True)
        
        # Configure retry policy
        self._retry_config = self.config.options.get('retry', {
            'max_retries': 3,
            'delay': 1,
            'backoff_factor': 2,
            'exceptions': (HandlerError,)
        })
    
    def add_pre_process_hook(self, hook: Callable[[Path, Dict[str, Any]], Awaitable[None]]) -> None:
        """Add a hook to run before processing."""
        self._pre_process_hooks.append(hook)
    
    def add_post_process_hook(self, hook: Callable[[HandlerResult], Awaitable[None]]) -> None:
        """Add a hook to run after processing."""
        self._post_process_hooks.append(hook)
    
    def add_error_hook(self, hook: Callable[[Exception, HandlerResult], Awaitable[None]]) -> None:
        """Add a hook to run on error."""
        self._error_hooks.append(hook)
    
    @abstractmethod
    def can_handle(
        self,
        file_path: Path,
        attachments: Optional[List[Path]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Determine if this handler can process the given file(s).
        
        Args:
            file_path: Primary file to process
            attachments: Optional list of attachment files
            context: Optional processing context
            
        Returns:
            bool: True if this handler can process the file(s)
        """
        pass
    
    @abstractmethod
    async def process(
        self,
        file_path: Path,
        context: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Path]] = None
    ) -> HandlerResult:
        """Process the file and any attachments.
        
        Args:
            file_path: Primary file to process
            context: Optional processing context
            attachments: Optional list of attachment files
            
        Returns:
            HandlerResult containing processing results
            
        Raises:
            HandlerError: If processing fails
        """
        pass
    
    def validate_output(self, result: HandlerResult) -> bool:
        """Validate processing results.
        
        Args:
            result: HandlerResult to validate
            
        Returns:
            bool: True if results are valid
        """
        # Basic validation that all handlers should pass
        if not isinstance(result, HandlerResult):
            self.logger.error("Result must be a HandlerResult instance")
            return False
            
        if not result.content and not result.processed_files:
            self.logger.error("Result must have either content or processed files")
            return False
            
        # Validate metrics
        if not result.metrics:
            self.logger.warning("No metrics recorded in result")
            
        # Validate timing
        if not result.start_time or not result.end_time:
            self.logger.warning("Missing timing information in result")
            
        return True
    
    async def rollback(self, result: HandlerResult) -> None:
        """Rollback changes if processing fails.
        
        Args:
            result: HandlerResult to rollback
        """
        try:
            # Clean up any processed files
            for file_path in result.processed_files:
                try:
                    await self.file_ops.delete_file(file_path)
                except Exception as e:
                    self.logger.error(f"Failed to delete {file_path}: {str(e)}")
            
            # Clean up any processed attachments
            for file_path in result.processed_attachments:
                try:
                    await self.file_ops.delete_file(file_path)
                except Exception as e:
                    self.logger.error(f"Failed to delete {file_path}: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"Error during rollback: {str(e)}")
    
    def get_option(self, key: str, default: Any = None) -> Any:
        """Get option from config.
        
        Args:
            key: Option key
            default: Default value if not found
            
        Returns:
            Option value
        """
        return self.config.options.get(key, default)
    
    def update_stats(self, result: HandlerResult) -> None:
        """Update handler statistics.
        
        Args:
            result: HandlerResult to update stats from
        """
        self.stats['processed'] += len(result.processed_files) + len(result.processed_attachments)
        self.stats['errors'] += len(result.errors)
        self.stats['warnings'] += len(result.warnings)
        
        # Update metrics
        self.metrics.update(result.metrics)
        
        # Update cache stats
        if self._cache_enabled:
            self.stats['cache_hits'] = self.metrics.get('cache_hits', 0)
            self.stats['cache_misses'] = self.metrics.get('cache_misses', 0)
    
    def log_result(self, result: HandlerResult) -> None:
        """Log processing result.
        
        Args:
            result: HandlerResult to log
        """
        if result.errors:
            for error in result.errors:
                self.logger.error(error)
                
        if result.warnings:
            for warning in result.warnings:
                self.logger.warning(warning)
                
        self.logger.info(
            f"Processed {len(result.processed_files)} files and "
            f"{len(result.processed_attachments)} attachments in "
            f"{result.processing_time:.2f} seconds"
        )
        
        # Log metrics
        if result.metrics:
            self.logger.debug("Processing metrics:")
            for key, value in result.metrics.items():
                self.logger.debug(f"  {key}: {value}")
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Clear cache if enabled
            if self._cache_enabled:
                self._cache.clear()
            
            # Run custom cleanup
            await self._cleanup()
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
    
    async def _cleanup(self) -> None:
        """Custom cleanup implementation.
        
        Override this method to implement custom cleanup logic.
        """
        pass
    
    async def _run_pre_process_hooks(self, file_path: Path, context: Dict[str, Any]) -> None:
        """Run pre-process hooks."""
        for hook in self._pre_process_hooks:
            try:
                await hook(file_path, context)
            except Exception as e:
                self.logger.error(f"Error in pre-process hook: {str(e)}")
    
    async def _run_post_process_hooks(self, result: HandlerResult) -> None:
        """Run post-process hooks."""
        for hook in self._post_process_hooks:
            try:
                await hook(result)
            except Exception as e:
                self.logger.error(f"Error in post-process hook: {str(e)}")
    
    async def _run_error_hooks(self, error: Exception, result: HandlerResult) -> None:
        """Run error hooks."""
        for hook in self._error_hooks:
            try:
                await hook(error, result)
            except Exception as e:
                self.logger.error(f"Error in error hook: {str(e)}")
    
    @async_retry()
    async def __call__(
        self,
        file_path: Path,
        context: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Path]] = None
    ) -> HandlerResult:
        """Process file with error handling and logging.
        
        Args:
            file_path: Primary file to process
            context: Optional processing context
            attachments: Optional list of attachment files
            
        Returns:
            HandlerResult containing processing results
            
        Raises:
            HandlerError: If processing fails and cannot be recovered
        """
        if not self.can_handle(file_path, attachments, context):
            raise HandlerError(f"Handler {self.__class__.__name__} cannot handle {file_path}")
            
        context = context or {}
        start_time = datetime.now()
        
        try:
            # Run pre-process hooks
            await self._run_pre_process_hooks(file_path, context)
            
            # Process file
            result = await self.process(file_path, context, attachments)
            
            # Update timing information
            end_time = datetime.now()
            result.start_time = start_time
            result.end_time = end_time
            result.processing_time = (end_time - start_time).total_seconds()
            
            # Validate output
            if not self.validate_output(result):
                raise HandlerError(f"Invalid output from {self.__class__.__name__}")
                
            # Update stats and metrics
            self.update_stats(result)
            self.log_result(result)
            
            # Run post-process hooks
            await self._run_post_process_hooks(result)
            
            return result
            
        except Exception as e:
            self.logger.exception(f"Error processing {file_path}")
            
            # Create error result
            error_result = HandlerResult(
                errors=[f"Processing failed: {str(e)}"],
                processed_files=[file_path],
                processed_attachments=attachments or [],
                start_time=start_time,
                end_time=datetime.now()
            )
            
            # Run error hooks and rollback
            await self._run_error_hooks(e, error_result)
            await self.rollback(error_result)
            
            # Update retry stats
            self.stats['retries'] += 1
            
            raise HandlerError(f"Processing failed: {str(e)}")
            
        finally:
            # Always update metrics
            self.metrics.record('processing_time', result.processing_time if 'result' in locals() else 0)
            self.metrics.record('retries', self.stats['retries']) 