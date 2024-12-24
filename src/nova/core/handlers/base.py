"""Base handler for Nova document processor."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from ..utils.logging import LoggerMixin

class BaseHandler(ABC, LoggerMixin):
    """Base class for all handlers."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the handler.
        
        Args:
            config: Handler configuration
        """
        self.config = config
    
    def validate_config(self) -> None:
        """Validate handler configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        if not isinstance(self.config, dict):
            raise ValueError("Handler config must be a dictionary")
    
    def get_option(self, key: str, default: Any = None) -> Any:
        """Get option from config.
        
        Args:
            key: Option key
            default: Default value if key not found
            
        Returns:
            Option value
        """
        return self.config.get(key, default)
    
    @abstractmethod
    async def process(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process content.
        
        Args:
            content: Content to process
            context: Optional processing context
            
        Returns:
            Dict containing processing results
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Handlers must implement process method") 