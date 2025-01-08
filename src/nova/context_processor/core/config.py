"""Configuration module for Nova document processor."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class NovaConfig(BaseModel):
    """Nova configuration model."""

    # Base directories
    base_dir: Path = Field(..., description="Base directory for Nova")
    input_dir: Path = Field(..., description="Input directory")
    output_dir: Path = Field(..., description="Output directory")
    processing_dir: Path = Field(..., description="Processing directory")
    
    # Processing options
    max_retries: int = Field(default=3, description="Maximum number of retries for processing")
    retry_delay: float = Field(default=1.0, description="Delay between retries in seconds")
    
    # File patterns
    include_patterns: List[str] = Field(default_factory=list, description="Patterns to include")
    exclude_patterns: List[str] = Field(default_factory=list, description="Patterns to exclude")
    
    # Handler options
    handler_options: Dict[str, Any] = Field(default_factory=dict, description="Handler-specific options")

    @classmethod
    def from_yaml(cls, config_path: Path) -> "NovaConfig":
        """Load configuration from YAML file.

        Args:
            config_path: Path to YAML file

        Returns:
            NovaConfig: Configuration instance
        """
        try:
            # Load YAML file
            with open(config_path) as f:
                config_data = yaml.safe_load(f)
            
            # Convert paths to Path objects
            for key in ["base_dir", "input_dir", "output_dir", "processing_dir"]:
                if key in config_data:
                    config_data[key] = Path(config_data[key])
            
            # Create instance
            return cls(**config_data)
        
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            raise

    def get_handler_option(self, handler_name: str, option_name: str, default: Any = None) -> Any:
        """Get handler-specific option.

        Args:
            handler_name: Name of handler
            option_name: Name of option
            default: Default value if not found

        Returns:
            Any: Option value
        """
        handler_opts = self.handler_options.get(handler_name, {})
        return handler_opts.get(option_name, default)

    def should_process_file(self, file_path: Path) -> bool:
        """Check if file should be processed.

        Args:
            file_path: Path to file

        Returns:
            bool: True if file should be processed
        """
        # Get relative path as string
        rel_path = str(file_path.relative_to(self.base_dir))
        
        # Check exclude patterns first
        for pattern in self.exclude_patterns:
            if file_path.match(pattern):
                return False
        
        # If no include patterns, process all files
        if not self.include_patterns:
            return True
        
        # Check include patterns
        for pattern in self.include_patterns:
            if file_path.match(pattern):
                return True
        
        return False 