from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional

class BaseConverter(ABC):
    """Base class for attachment converters."""
    
    @abstractmethod
    async def convert(self, file_path: Path) -> Optional[str]:
        """Convert attachment to markdown/text content.
        
        Args:
            file_path: Path to file
            
        Returns:
            Converted content or None
        """
        pass
        
    @abstractmethod
    async def get_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Get attachment metadata.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary of metadata
        """
        pass 