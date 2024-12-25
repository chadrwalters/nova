"""Base handler interface for all pipeline phases."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime

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

class BaseHandler(ABC):
    """Base class for all handlers in the pipeline.
    
    This unified base handler combines functionality from parse and consolidate phases,
    providing a consistent interface across the pipeline.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the handler with optional configuration."""
        self.config = config or {}
        self._pre_process_hooks: List[Callable[[Path, Dict[str, Any]], Awaitable[None]]] = []
        self._post_process_hooks: List[Callable[[HandlerResult], Awaitable[None]]] = []
        self._error_hooks: List[Callable[[Exception, HandlerResult], Awaitable[None]]] = []
    
    def get_option(self, key: str, default: Any = None) -> Any:
        """Get option from config.
        
        Args:
            key: Option key
            default: Default value if not found
            
        Returns:
            Option value
        """
        if isinstance(self.config, dict):
            return self.config.get(key, default)
        return getattr(self.config, key, default)
    
    def add_pre_process_hook(self, hook: Callable[[Path, Dict[str, Any]], Awaitable[None]]) -> None:
        """Add a hook to run before processing."""
        self._pre_process_hooks.append(hook)
    
    def add_post_process_hook(self, hook: Callable[[HandlerResult], Awaitable[None]]) -> None:
        """Add a hook to run after processing."""
        self._post_process_hooks.append(hook)
    
    def add_error_hook(self, hook: Callable[[Exception, HandlerResult], Awaitable[None]]) -> None:
        """Add a hook to run on error."""
        self._error_hooks.append(hook)
    
    async def _pre_process(self, file_path: Path, context: Dict[str, Any]) -> None:
        """Run pre-process hooks."""
        for hook in self._pre_process_hooks:
            await hook(file_path, context)
    
    async def _post_process(self, result: HandlerResult) -> None:
        """Run post-process hooks."""
        for hook in self._post_process_hooks:
            await hook(result)
    
    async def _on_error(self, error: Exception, result: HandlerResult) -> None:
        """Run error hooks."""
        for hook in self._error_hooks:
            await hook(error, result)
    
    @abstractmethod
    def can_handle(self, file_path: Path, attachments: Optional[List[Path]] = None) -> bool:
        """Determine if this handler can process the given file and optional attachments.
        
        Args:
            file_path: Path to the main file
            attachments: Optional list of paths to attachments
            
        Returns:
            bool: True if this handler can process the file/attachments
        """
        pass
    
    @abstractmethod
    async def process(
        self, 
        file_path: Path, 
        context: Dict[str, Any],
        attachments: Optional[List[Path]] = None
    ) -> HandlerResult:
        """Process the file and optional attachments.
        
        Args:
            file_path: Path to the main file
            context: Additional context for processing
            attachments: Optional list of paths to attachments
            
        Returns:
            HandlerResult containing processing results and metadata
        """
        pass
    
    @abstractmethod
    def validate_output(self, result: HandlerResult) -> bool:
        """Validate the processing results.
        
        Args:
            result: The HandlerResult to validate
            
        Returns:
            bool: True if results are valid
        """
        pass
    
    async def cleanup(self) -> None:
        """Clean up any resources."""
        pass 