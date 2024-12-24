"""Base processor class for Nova document processor."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from ..config.base import ProcessorConfig
from ..utils.logging import get_logger

class BaseProcessor(ABC):
    """Base class for all processors."""
    
    def __init__(self, config: ProcessorConfig):
        """Initialize the processor.
        
        Args:
            config: Processor configuration
        """
        self.config = config
        self.logger = get_logger(self.__class__.__name__)
    
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
            Dict containing:
                - content: Processed content
                - metadata: Processing metadata
        """
        pass
    
    def validate_config(self) -> None:
        """Validate processor configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Base validation - override in subclasses
        if not self.config:
            raise ValueError("No configuration provided")
    
    def get_option(self, key: str, default: Any = None) -> Any:
        """Get configuration option.
        
        Args:
            key: Option key
            default: Default value if not found
            
        Returns:
            Option value
        """
        return self.config.options.get(key, default)
    
    def set_option(self, key: str, value: Any) -> None:
        """Set configuration option.
        
        Args:
            key: Option key
            value: Option value
        """
        self.config.options[key] = value
    
    def log_debug(self, message: str) -> None:
        """Log debug message.
        
        Args:
            message: Message to log
        """
        self.logger.debug(message)
    
    def log_info(self, message: str) -> None:
        """Log info message.
        
        Args:
            message: Message to log
        """
        self.logger.info(message)
    
    def log_warning(self, message: str) -> None:
        """Log warning message.
        
        Args:
            message: Message to log
        """
        self.logger.warning(message)
    
    def log_error(self, message: str) -> None:
        """Log error message.
        
        Args:
            message: Message to log
        """
        self.logger.error(message) 