"""Path utilities for file operations."""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

from ..errors import PipelineError

def get_workspace_path(path: Union[str, Path]) -> Path:
    """Get absolute path in workspace.
    
    Args:
        path: Path relative to workspace root
        
    Returns:
        Absolute path
    """
    try:
        workspace_root = Path(os.environ.get('NOVA_BASE_DIR', ''))
        if not workspace_root:
            raise PipelineError("NOVA_BASE_DIR environment variable not set")
        
        return workspace_root / path
        
    except Exception as e:
        raise PipelineError(f"Failed to get workspace path: {e}")

def get_input_path(path: Union[str, Path]) -> Path:
    """Get absolute path in input directory.
    
    Args:
        path: Path relative to input directory
        
    Returns:
        Absolute path
    """
    try:
        input_dir = Path(os.environ.get('NOVA_INPUT_DIR', ''))
        if not input_dir:
            raise PipelineError("NOVA_INPUT_DIR environment variable not set")
        
        return input_dir / path
        
    except Exception as e:
        raise PipelineError(f"Failed to get input path: {e}")

def get_output_path(path: Union[str, Path]) -> Path:
    """Get absolute path in output directory.
    
    Args:
        path: Path relative to output directory
        
    Returns:
        Absolute path
    """
    try:
        output_dir = Path(os.environ.get('NOVA_OUTPUT_DIR', ''))
        if not output_dir:
            raise PipelineError("NOVA_OUTPUT_DIR environment variable not set")
        
        return output_dir / path
        
    except Exception as e:
        raise PipelineError(f"Failed to get output path: {e}")

def get_temp_path(path: Union[str, Path]) -> Path:
    """Get absolute path in temp directory.
    
    Args:
        path: Path relative to temp directory
        
    Returns:
        Absolute path
    """
    try:
        temp_dir = Path(os.environ.get('NOVA_TEMP_DIR', ''))
        if not temp_dir:
            raise PipelineError("NOVA_TEMP_DIR environment variable not set")
        
        return temp_dir / path
        
    except Exception as e:
        raise PipelineError(f"Failed to get temp path: {e}")

def get_phase_path(phase: str, path: Union[str, Path]) -> Path:
    """Get absolute path in phase directory.
    
    Args:
        phase: Phase name
        path: Path relative to phase directory
        
    Returns:
        Absolute path
    """
    try:
        phase_dir = Path(os.environ.get(f'NOVA_PHASE_{phase.upper()}', ''))
        if not phase_dir:
            raise PipelineError(f"NOVA_PHASE_{phase.upper()} environment variable not set")
        
        return phase_dir / path
        
    except Exception as e:
        raise PipelineError(f"Failed to get phase path: {e}")

def get_image_path(path: Union[str, Path], subdir: str = 'original') -> Path:
    """Get absolute path in image directory.
    
    Args:
        path: Path relative to image directory
        subdir: Subdirectory (original, processed, metadata, cache)
        
    Returns:
        Absolute path
    """
    try:
        image_dir = Path(os.environ.get('NOVA_IMAGES_DIR', ''))
        if not image_dir:
            raise PipelineError("NOVA_IMAGES_DIR environment variable not set")
        
        return image_dir / subdir / path
        
    except Exception as e:
        raise PipelineError(f"Failed to get image path: {e}")

def get_office_path(path: Union[str, Path], subdir: str = 'assets') -> Path:
    """Get absolute path in office directory.
    
    Args:
        path: Path relative to office directory
        subdir: Subdirectory (assets, temp)
        
    Returns:
        Absolute path
    """
    try:
        office_dir = Path(os.environ.get('NOVA_OFFICE_DIR', ''))
        if not office_dir:
            raise PipelineError("NOVA_OFFICE_DIR environment variable not set")
        
        return office_dir / subdir / path
        
    except Exception as e:
        raise PipelineError(f"Failed to get office path: {e}")

def ensure_directory(path: Union[str, Path]) -> Path:
    """Ensure directory exists.
    
    Args:
        path: Directory path
        
    Returns:
        Directory path
    """
    try:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path
        
    except Exception as e:
        raise PipelineError(f"Failed to ensure directory exists: {e}")

def clean_directory(path: Union[str, Path]) -> None:
    """Clean directory contents.
    
    Args:
        path: Directory path
    """
    try:
        path = Path(path)
        if path.exists():
            for item in path.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    clean_directory(item)
                    item.rmdir()
                    
    except Exception as e:
        raise PipelineError(f"Failed to clean directory: {e}")

def copy_file(src: Union[str, Path], dst: Union[str, Path]) -> None:
    """Copy file.
    
    Args:
        src: Source path
        dst: Destination path
    """
    try:
        src = Path(src)
        dst = Path(dst)
        
        if not src.exists():
            raise PipelineError(f"Source file does not exist: {src}")
        
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        
    except Exception as e:
        raise PipelineError(f"Failed to copy file: {e}")

def move_file(src: Union[str, Path], dst: Union[str, Path]) -> None:
    """Move file.
    
    Args:
        src: Source path
        dst: Destination path
    """
    try:
        src = Path(src)
        dst = Path(dst)
        
        if not src.exists():
            raise PipelineError(f"Source file does not exist: {src}")
        
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        
    except Exception as e:
        raise PipelineError(f"Failed to move file: {e}")

def delete_file(path: Union[str, Path]) -> None:
    """Delete file.
    
    Args:
        path: File path
    """
    try:
        path = Path(path)
        if path.exists():
            path.unlink()
            
    except Exception as e:
        raise PipelineError(f"Failed to delete file: {e}")

def get_relative_path(path: Union[str, Path], base: Union[str, Path]) -> Path:
    """Get relative path.
    
    Args:
        path: Path to make relative
        base: Base path
        
    Returns:
        Relative path
    """
    try:
        path = Path(path)
        base = Path(base)
        return path.relative_to(base)
        
    except Exception as e:
        raise PipelineError(f"Failed to get relative path: {e}")

def get_file_size(path: Union[str, Path]) -> int:
    """Get file size in bytes.
    
    Args:
        path: File path
        
    Returns:
        File size in bytes
    """
    try:
        path = Path(path)
        if not path.exists():
            raise PipelineError(f"File does not exist: {path}")
        
        return path.stat().st_size
        
    except Exception as e:
        raise PipelineError(f"Failed to get file size: {e}")

def get_file_mtime(path: Union[str, Path]) -> float:
    """Get file modification time.
    
    Args:
        path: File path
        
    Returns:
        Modification time as Unix timestamp
    """
    try:
        path = Path(path)
        if not path.exists():
            raise PipelineError(f"File does not exist: {path}")
        
        return path.stat().st_mtime
        
    except Exception as e:
        raise PipelineError(f"Failed to get file modification time: {e}")

def get_file_hash(path: Union[str, Path]) -> str:
    """Get file hash.
    
    Args:
        path: File path
        
    Returns:
        File hash
    """
    try:
        import hashlib
        
        path = Path(path)
        if not path.exists():
            raise PipelineError(f"File does not exist: {path}")
        
        hasher = hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        
        return hasher.hexdigest()
        
    except Exception as e:
        raise PipelineError(f"Failed to get file hash: {e}") 