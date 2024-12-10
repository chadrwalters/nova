"""Configuration management for the application."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from src.core.exceptions import ConfigurationError

# Load environment variables
load_dotenv()

class ProcessingConfig:
    """Configuration for document processing."""

    def __init__(
        self,
        input_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        processing_dir: Optional[Path] = None,
        error_tolerance: str = "strict"
    ) -> None:
        """Initialize processing configuration.
        
        Args:
            input_dir: Directory containing input files
            output_dir: Directory for output files
            processing_dir: Directory for temporary processing files
            error_tolerance: Error handling mode ("strict" or "lenient")
            
        Raises:
            ConfigurationError: If required configuration is missing or invalid
        """
        # Get directories from environment or parameters
        self.input_dir = input_dir or Path(os.getenv("NOVA_INPUT_DIR", "input"))
        self.output_dir = output_dir or Path(os.getenv("NOVA_OUTPUT_DIR", "output"))
        self.processing_dir = processing_dir or Path(os.getenv("NOVA_PROCESSING_DIR", "processing"))
        
        # Validate directories
        if not self.input_dir:
            raise ConfigurationError("Input directory not configured", config_key="NOVA_INPUT_DIR")
        if not self.output_dir:
            raise ConfigurationError("Output directory not configured", config_key="NOVA_OUTPUT_DIR")
        if not self.processing_dir:
            raise ConfigurationError("Processing directory not configured", config_key="NOVA_PROCESSING_DIR")
            
        # Create subdirectories
        self.temp_dir = self.processing_dir / "temp"
        self.media_dir = self.processing_dir / "media"
        self.html_dir = self.processing_dir / "html"
        self.attachments_dir = self.processing_dir / "attachments"
        self.consolidated_dir = self.processing_dir / "consolidated"
        
        # Error handling mode
        if error_tolerance not in ["strict", "lenient"]:
            raise ConfigurationError(
                f"Invalid error tolerance mode: {error_tolerance}",
                config_key="error_tolerance"
            )
        self.error_tolerance = error_tolerance == "lenient"
        
    def create_directories(self) -> None:
        """Create all required directories.
        
        Raises:
            ConfigurationError: If directory creation fails
        """
        try:
            for directory in [
                self.input_dir,
                self.output_dir,
                self.processing_dir,
                self.temp_dir,
                self.media_dir,
                self.html_dir,
                self.attachments_dir,
                self.consolidated_dir
            ]:
                directory.mkdir(parents=True, exist_ok=True)
        except Exception as err:
            raise ConfigurationError(
                f"Failed to create directories: {err}",
                config_key="directory_creation"
            ) from err
