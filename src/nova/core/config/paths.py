"""Path management module for Nova document processor."""

import os
from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field
from .logging import get_logger

class PathsConfig(BaseModel):
    """Configuration for file paths."""
    base_dir: str = Field(default=".")
    input_dir: str = Field(default="input")
    output_dir: str = Field(default="output")
    processing_dir: str = Field(default="processing")
    temp_dir: str = Field(default="temp")
    state_dir: str = Field(default="state")
    phase_dirs: Dict[str, str] = Field(default_factory=lambda: {
        'markdown_parse': 'phase/markdown_parse',
        'markdown_consolidate': 'phase/markdown_consolidate',
        'markdown_aggregate': 'phase/markdown_aggregate',
        'markdown_split': 'phase/markdown_split'
    })
    image_dirs: Dict[str, str] = Field(default_factory=lambda: {
        'original': 'images/original',
        'processed': 'images/processed',
        'metadata': 'images/metadata',
        'cache': 'images/cache'
    })
    office_dirs: Dict[str, str] = Field(default_factory=lambda: {
        'assets': 'office/assets',
        'temp': 'office/temp'
    })
    
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=False,
        extra='forbid'
    )

class NovaPaths(BaseModel):
    """Centralized path management for Nova document processor."""
    
    # Base directories
    base_dir: Path
    input_dir: Path
    output_dir: Path
    processing_dir: Path
    temp_dir: Path
    state_dir: Path
    
    # Phase directories
    phase_dirs: Dict[str, Path] = {
        'markdown_parse': None,
        'markdown_consolidate': None,
        'markdown_aggregate': None,
        'markdown_split': None
    }
    
    # Image directories
    image_dirs: Dict[str, Path] = {
        'original': None,
        'processed': None,
        'metadata': None,
        'cache': None
    }
    
    # Office directories
    office_dirs: Dict[str, Path] = {
        'assets': None,
        'temp': None
    }
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    @classmethod
    def from_env(cls) -> 'NovaPaths':
        """Create NovaPaths instance from environment variables."""
        base_dir = Path(os.getenv('NOVA_BASE_DIR', '.')).resolve()
        processing_dir = Path(os.getenv('NOVA_PROCESSING_DIR', base_dir / '_NovaProcessing'))
        
        # Ensure all paths are derived from base_dir
        input_dir = Path(os.getenv('NOVA_INPUT_DIR', base_dir / '_NovaInput'))
        output_dir = Path(os.getenv('NOVA_OUTPUT_DIR', base_dir / '_NovaOutput'))
        temp_dir = Path(os.getenv('NOVA_TEMP_DIR', processing_dir / 'temp'))
        
        return cls(
            base_dir=base_dir,
            input_dir=input_dir,
            output_dir=output_dir,
            processing_dir=processing_dir,
            temp_dir=temp_dir,
            state_dir=processing_dir / '.state',
            phase_dirs={
                'markdown_parse': processing_dir / 'phases/markdown_parse',
                'markdown_consolidate': processing_dir / 'phases/markdown_consolidate',
                'markdown_aggregate': processing_dir / 'phases/markdown_aggregate',
                'markdown_split': processing_dir / 'phases/markdown_split'
            },
            image_dirs={
                'original': processing_dir / 'images/original',
                'processed': processing_dir / 'images/processed',
                'metadata': processing_dir / 'images/metadata',
                'cache': processing_dir / 'images/cache'
            },
            office_dirs={
                'assets': processing_dir / 'office/assets',
                'temp': processing_dir / 'office/temp'
            }
        )
    
    def create_directories(self) -> None:
        """Create all required directories."""
        logger = get_logger(__name__)
        
        try:
            # Create base directories
            for dir_path in [
                self.base_dir,
                self.input_dir,
                self.output_dir,
                self.processing_dir,
                self.temp_dir,
                self.state_dir
            ]:
                logger.info(f"Creating directory: {dir_path}")
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    # Only log error and continue if directory exists
                    if e.errno != 17:  # 17 is EEXIST
                        logger.error(f"Failed to create directory {dir_path}: {e}")
                        raise
                    logger.debug(f"Directory already exists: {dir_path}")
            
            # Create phase directories
            for dir_path in self.phase_dirs.values():
                if dir_path:  # Only create if path is set
                    logger.info(f"Creating phase directory: {dir_path}")
                    dir_path.mkdir(parents=True, exist_ok=True)
            
            # Create image directories
            for dir_path in self.image_dirs.values():
                if dir_path:  # Only create if path is set
                    logger.info(f"Creating image directory: {dir_path}")
                    dir_path.mkdir(parents=True, exist_ok=True)
            
            # Create office directories
            for dir_path in self.office_dirs.values():
                if dir_path:  # Only create if path is set
                    logger.info(f"Creating office directory: {dir_path}")
                    dir_path.mkdir(parents=True, exist_ok=True)
                
        except Exception as e:
            if getattr(e, 'errno', None) != 17:  # Only raise if not EEXIST
                logger.error(f"Error creating directories: {e}")
                raise
            logger.debug(f"Some directories already exist")
    
    def get_relative_path(self, path: Path) -> Path:
        """Get path relative to base directory.
        
        Args:
            path: Path to make relative
            
        Returns:
            Path relative to base directory
        """
        try:
            return path.relative_to(self.base_dir)
        except ValueError:
            return path 