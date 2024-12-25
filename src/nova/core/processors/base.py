"""Base processor implementation."""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

from nova.core.config import ProcessorConfig, PipelineConfig
from nova.core.utils.logging import get_logger
from nova.core.errors import ConfigurationError, StateError

class BaseProcessor(ABC):
    """Base class for all processors."""

    def __init__(self, processor_config: ProcessorConfig, pipeline_config: PipelineConfig):
        """Initialize the processor.
        
        Args:
            processor_config: Processor-specific configuration
            pipeline_config: Pipeline-wide configuration
        """
        self.config = processor_config
        self.pipeline_config = pipeline_config
        self.logger = get_logger(self.__class__.__name__)
        
        # Set up paths
        self.input_dir = Path(processor_config.input_dir)
        self.output_dir = Path(processor_config.output_dir)
        self.temp_dir = pipeline_config.paths.temp_dir
        
        # Initialize state
        self._initialized = False
        self._active = False
    
    def _verify_directories(self) -> None:
        """Verify required directories exist and are writable.
        
        Raises:
            ConfigurationError: If directory verification fails
            StateError: If directory creation fails
        """
        try:
            # Verify input directory exists
            if not self.input_dir.exists():
                raise ConfigurationError(f"Input directory does not exist: {self.input_dir}")
            if not self.input_dir.is_dir():
                raise ConfigurationError(f"Input path is not a directory: {self.input_dir}")
            if not os.access(self.input_dir, os.R_OK):
                raise ConfigurationError(f"Input directory is not readable: {self.input_dir}")
            
            # Create and verify output directory
            if not self.output_dir.exists():
                self.logger.info(f"Creating output directory: {self.output_dir}")
                self.output_dir.mkdir(parents=True, exist_ok=True)
            if not self.output_dir.is_dir():
                raise ConfigurationError(f"Output path is not a directory: {self.output_dir}")
            if not os.access(self.output_dir, os.W_OK):
                raise ConfigurationError(f"Output directory is not writable: {self.output_dir}")
            
            # Set output directory permissions
            self.output_dir.chmod(0o755)
            
            # Create and verify temp directory
            if not self.temp_dir.exists():
                self.logger.info(f"Creating temp directory: {self.temp_dir}")
                self.temp_dir.mkdir(parents=True, exist_ok=True)
            if not self.temp_dir.is_dir():
                raise ConfigurationError(f"Temp path is not a directory: {self.temp_dir}")
            if not os.access(self.temp_dir, os.W_OK):
                raise ConfigurationError(f"Temp directory is not writable: {self.temp_dir}")
            
            # Set temp directory permissions
            self.temp_dir.chmod(0o755)
            
        except (OSError, PermissionError) as e:
            raise StateError(f"Failed to verify/create directories: {e}")
    
    async def initialize(self) -> None:
        """Initialize the processor.
        
        This method should be called before processing begins.
        It verifies the directory structure and performs any necessary setup.
        
        Raises:
            ConfigurationError: If initialization fails due to configuration
            StateError: If initialization fails due to system state
        """
        if self._initialized:
            return
            
        self.logger.info("Initializing processor...")
        
        try:
            # Verify directories
            self._verify_directories()
            
            # Perform processor-specific initialization
            await self._initialize()
            
            self._initialized = True
            self.logger.info("Processor initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize processor: {e}")
            raise
    
    @abstractmethod
    async def _initialize(self) -> None:
        """Perform processor-specific initialization.
        
        This method should be implemented by subclasses to perform any
        necessary setup beyond directory verification.
        
        Raises:
            ConfigurationError: If initialization fails due to configuration
            StateError: If initialization fails due to system state
        """
        pass
    
    async def cleanup(self) -> None:
        """Clean up processor resources.
        
        This method should be called when processing is complete.
        """
        if not self._initialized:
            return
            
        self.logger.info("Cleaning up processor...")
        
        try:
            # Perform processor-specific cleanup
            await self._cleanup()
            
            self._initialized = False
            self.logger.info("Processor cleanup complete")
            
        except Exception as e:
            self.logger.error(f"Failed to clean up processor: {e}")
            raise
    
    @abstractmethod
    async def _cleanup(self) -> None:
        """Perform processor-specific cleanup.
        
        This method should be implemented by subclasses to perform any
        necessary cleanup beyond basic resource management.
        """
        pass
    
    async def __aenter__(self) -> 'BaseProcessor':
        """Enter the runtime context for using the processor."""
        await self.initialize()
        self._active = True
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the runtime context and clean up resources."""
        self._active = False
        await self.cleanup()
    
    @property
    def is_initialized(self) -> bool:
        """Whether the processor has been initialized."""
        return self._initialized
    
    @property
    def is_active(self) -> bool:
        """Whether the processor is currently active."""
        return self._active 