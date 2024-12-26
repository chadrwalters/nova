"""Command for cleaning up Nova processing directories."""

import click
from pathlib import Path
import os
import shutil
import platform
import subprocess
from typing import List, Dict, Optional, Tuple, Union
from datetime import datetime, timedelta

from ...core.logging import get_logger
from ...core.processors.base import BaseProcessor
from ...core.config import load_config
from ...core.errors import ConfigurationError

logger = get_logger(__name__)

class DirectorySpec:
    """Directory specification with cleanup rules."""
    def __init__(
        self,
        path: Path,
        create: bool = True,
        perms: int = 0o755,
        max_size: Optional[int] = None,  # MB
        min_free: Optional[int] = None,  # MB
        cleanup_age: Optional[int] = None  # days
    ):
        self.path = path
        self.create = create
        self.perms = perms
        self.max_size = max_size
        self.min_free = min_free
        self.cleanup_age = cleanup_age

@click.command()
@click.option('--force', '-f', is_flag=True, help='Force cleanup without confirmation')
@click.option('--dry-run', '-n', is_flag=True, help='Show what would be cleaned without actually deleting')
@click.option('--include-input', '-i', is_flag=True, help='Also clean input directory (USE WITH CAUTION)')
def cleanup(force: bool, dry_run: bool, include_input: bool):
    """Clean up Nova processing directories and resources."""
    # Clean temp files
    specs = get_temp_directories()
    if include_input:
        specs.extend(get_processing_directories())
    _clean_directories(specs, force, dry_run)

def get_temp_directories() -> List[Path]:
    """Get list of temporary directories to clean."""
    return [
        Path(os.path.expandvars(os.environ.get('NOVA_TEMP_DIR', ''))),
        Path(os.path.expandvars(os.environ.get('NOVA_OFFICE_TEMP_DIR', ''))),
        Path(os.path.expandvars(os.environ.get('NOVA_IMAGE_CACHE_DIR', '')))
    ]

def get_processing_directories() -> List[DirectorySpec]:
    """Get list of processing directories to clean."""
    return [
        DirectorySpec(Path(os.path.expandvars(os.environ.get('NOVA_PHASE_MARKDOWN_PARSE', '')))),
        DirectorySpec(Path(os.path.expandvars(os.environ.get('NOVA_PHASE_MARKDOWN_CONSOLIDATE', '')))),
        DirectorySpec(Path(os.path.expandvars(os.environ.get('NOVA_PHASE_MARKDOWN_AGGREGATE', '')))),
        DirectorySpec(Path(os.path.expandvars(os.environ.get('NOVA_PHASE_MARKDOWN_SPLIT', '')))),
        DirectorySpec(Path(os.path.expandvars(os.environ.get('NOVA_PROCESSED_IMAGES_DIR', ''))), max_size=2048),
        DirectorySpec(Path(os.path.expandvars(os.environ.get('NOVA_IMAGE_METADATA_DIR', ''))))
    ]

def get_required_directories() -> List[DirectorySpec]:
    """Get list of required directories to verify."""
    return [
        DirectorySpec(Path(os.path.expandvars(os.environ.get('NOVA_BASE_DIR', '')))),
        DirectorySpec(Path(os.path.expandvars(os.environ.get('NOVA_INPUT_DIR', '')))),
        DirectorySpec(Path(os.path.expandvars(os.environ.get('NOVA_OUTPUT_DIR', '')))),
        DirectorySpec(Path(os.path.expandvars(os.environ.get('NOVA_PROCESSING_DIR', '')))),
        DirectorySpec(Path(os.path.expandvars(os.environ.get('NOVA_STATE_DIR', ''))), perms=0o700)
    ]

def _clean_directories(specs: List[Union[Path, DirectorySpec]], force: bool = False, dry_run: bool = False) -> None:
    """Clean directories according to their specifications."""
    logger.info("Cleaning temporary files and processing directories...")
    
    for spec in specs:
        # Handle both Path and DirectorySpec objects
        path = spec.path if isinstance(spec, DirectorySpec) else spec
        if not path.name:  # Skip if path is empty
            continue
            
        logger.debug(f"Verifying directory: '{path}'")
        
        if path.exists():
            logger.info(f"Cleaning directory: {path}")
            try:
                if not dry_run:
                    # Remove all files
                    for file_path in path.glob('**/*'):
                        if file_path.is_file():
                            file_path.unlink()
                    
                    # Remove empty directories
                    for dir_path in sorted(path.glob('**/*'), reverse=True):
                        if dir_path.is_dir() and not any(dir_path.iterdir()):
                            dir_path.rmdir()
                            
            except Exception as e:
                logger.error(f"Error cleaning {path}: {str(e)}")
    
    logger.info("All processing directories cleaned") 