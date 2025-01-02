"""Centralized output file management for Nova."""

from pathlib import Path
from typing import Optional, Union
import logging

from nova.config.manager import ConfigManager

logger = logging.getLogger(__name__)

class OutputManager:
    """Centralized manager for file output paths and operations."""
    
    def __init__(self, config: ConfigManager):
        """Initialize output manager.
        
        Args:
            config: Nova configuration manager
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def get_output_path_for_phase(
        self,
        input_file: Union[str, Path],
        phase_name: str,
        extension: str = ".parsed.md",
    ) -> Path:
        """Get output path for a file in a specific phase.
        
        Args:
            input_file: Input file path
            phase_name: Name of the phase (e.g. "parse", "split")
            extension: File extension to use for output
            
        Returns:
            Path where output should be written
        """
        input_file = Path(input_file)
        
        # Get path relative to input directory
        try:
            relative_path = input_file.relative_to(self.config.input_dir)
        except ValueError:
            # If not under input_dir, use filename only
            relative_path = Path(input_file.name)
            
        # Build output path under phase directory
        output_base = self.config.processing_dir / "phases" / phase_name
        
        if input_file.is_dir():
            # For directories, create a directory with same name
            output_path = output_base / relative_path
        else:
            # For files, replace extension
            new_filename = f"{relative_path.stem}{extension}"
            output_path = output_base / relative_path.parent / new_filename
            
        # Ensure parent directories exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path
        
    def get_directory_for_phase(
        self,
        input_file: Union[str, Path],
        phase_name: str,
        create: bool = True
    ) -> Path:
        """Get output directory for a file in a specific phase.
        
        Args:
            input_file: Input file path
            phase_name: Name of the phase
            create: Whether to create the directory
            
        Returns:
            Path to output directory
        """
        input_file = Path(input_file)
        
        # Get path relative to input directory
        try:
            relative_path = input_file.relative_to(self.config.input_dir)
        except ValueError:
            relative_path = Path(input_file.name)
            
        # Build directory path
        output_base = self.config.processing_dir / "phases" / phase_name
        output_dir = output_base / relative_path.parent / relative_path.stem
        
        if create:
            output_dir.mkdir(parents=True, exist_ok=True)
            
        return output_dir
        
    def copy_file(
        self,
        source: Path,
        destination: Path,
        overwrite: bool = True
    ) -> bool:
        """Copy a file, creating parent directories if needed.
        
        Args:
            source: Source file path
            destination: Destination file path
            overwrite: Whether to overwrite existing files
            
        Returns:
            True if file was copied, False if skipped
        """
        try:
            if not source.exists():
                self.logger.warning(f"Source file does not exist: {source}")
                return False
                
            if destination.exists() and not overwrite:
                self.logger.debug(f"Skipping existing file: {destination}")
                return False
                
            # Ensure parent directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            destination.write_bytes(source.read_bytes())
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to copy {source} to {destination}: {str(e)}")
            return False 