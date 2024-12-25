"""Path utilities for Nova document processor."""

import hashlib
from pathlib import Path
from typing import Union, Optional

from ..errors import FileError
from .file_ops import FileOperationsManager

# Initialize file operations manager
file_ops = FileOperationsManager()

async def ensure_dir(path: Union[str, Path]) -> Path:
    """Ensure directory exists.
    
    Args:
        path: Directory path
        
    Returns:
        Path object for directory
        
    Raises:
        FileError: If directory cannot be created
    """
    try:
        path = Path(path)
        await file_ops.create_directory(path)
        return path
    except Exception as e:
        raise FileError(f"Failed to create directory {path}: {str(e)}") from e

async def ensure_file(path: Union[str, Path]) -> Path:
    """Ensure file exists.
    
    Args:
        path: File path
        
    Returns:
        Path object for file
        
    Raises:
        FileError: If file cannot be created
    """
    try:
        path = Path(path)
        await file_ops.create_directory(path.parent)
        await file_ops.touch_file(path)
        return path
    except Exception as e:
        raise FileError(f"Failed to create file {path}: {str(e)}") from e

async def clean_dir(path: Union[str, Path]) -> None:
    """Clean directory by removing all contents.
    
    Args:
        path: Directory path
        
    Raises:
        FileError: If directory cannot be cleaned
    """
    try:
        path = Path(path)
        if await file_ops.path_exists(path):
            await file_ops.remove_directory(path, recursive=True)
        await file_ops.create_directory(path)
    except Exception as e:
        raise FileError(f"Failed to clean directory {path}: {str(e)}") from e

async def copy_file(
    source: Union[str, Path],
    dest: Union[str, Path],
    overwrite: bool = True
) -> None:
    """Copy file from source to destination.
    
    Args:
        source: Source file path
        dest: Destination file path
        overwrite: Whether to overwrite existing file
        
    Raises:
        FileError: If file cannot be copied
    """
    try:
        source = Path(source)
        dest = Path(dest)
        
        # Check if source exists
        if not await file_ops.path_exists(source):
            raise FileError(f"Source file does not exist: {source}")
        
        # Check if destination exists
        if await file_ops.path_exists(dest) and not overwrite:
            raise FileError(f"Destination file exists: {dest}")
        
        # Create destination directory
        await file_ops.create_directory(dest.parent)
        
        # Copy file
        await file_ops.copy_file(source, dest)
    except Exception as e:
        raise FileError(f"Failed to copy file {source} to {dest}: {str(e)}") from e

async def move_file(
    source: Union[str, Path],
    dest: Union[str, Path],
    overwrite: bool = True
) -> None:
    """Move file from source to destination.
    
    Args:
        source: Source file path
        dest: Destination file path
        overwrite: Whether to overwrite existing file
        
    Raises:
        FileError: If file cannot be moved
    """
    try:
        source = Path(source)
        dest = Path(dest)
        
        # Check if source exists
        if not await file_ops.path_exists(source):
            raise FileError(f"Source file does not exist: {source}")
        
        # Check if destination exists
        if await file_ops.path_exists(dest) and not overwrite:
            raise FileError(f"Destination file exists: {dest}")
        
        # Create destination directory
        await file_ops.create_directory(dest.parent)
        
        # Move file
        await file_ops.move_file(source, dest)
    except Exception as e:
        raise FileError(f"Failed to move file {source} to {dest}: {str(e)}") from e

async def get_file_size(path: Union[str, Path]) -> int:
    """Get file size in bytes.
    
    Args:
        path: File path
        
    Returns:
        File size in bytes
        
    Raises:
        FileError: If file size cannot be determined
    """
    try:
        path = Path(path)
        stats = await file_ops.get_file_stats(path)
        return stats.st_size
    except Exception as e:
        raise FileError(f"Failed to get file size for {path}: {str(e)}") from e

async def get_file_mtime(path: Union[str, Path]) -> float:
    """Get file modification time.
    
    Args:
        path: File path
        
    Returns:
        Modification time as timestamp
        
    Raises:
        FileError: If modification time cannot be determined
    """
    try:
        path = Path(path)
        stats = await file_ops.get_file_stats(path)
        return stats.st_mtime
    except Exception as e:
        raise FileError(f"Failed to get modification time for {path}: {str(e)}") from e

async def get_file_hash(
    path: Union[str, Path],
    algorithm: str = 'sha256',
    chunk_size: int = 8192
) -> str:
    """Get file hash.
    
    Args:
        path: File path
        algorithm: Hash algorithm
        chunk_size: Size of chunks to read
        
    Returns:
        File hash as hex string
        
    Raises:
        FileError: If file hash cannot be computed
    """
    try:
        path = Path(path)
        hasher = hashlib.new(algorithm)
        
        async for chunk in file_ops.read_file_chunks(path, chunk_size):
            hasher.update(chunk)
        
        return hasher.hexdigest()
    except Exception as e:
        raise FileError(f"Failed to compute hash for {path}: {str(e)}") from e

def normalize_path(path: Union[str, Path]) -> Path:
    """Normalize path by resolving symlinks and relative components.
    
    Args:
        path: Path to normalize
        
    Returns:
        Normalized path
        
    Raises:
        FileError: If path cannot be normalized
    """
    try:
        return Path(path).resolve()
    except Exception as e:
        raise FileError(f"Failed to normalize path {path}: {str(e)}") from e

async def is_subpath(
    path: Union[str, Path],
    parent: Union[str, Path]
) -> bool:
    """Check if path is a subpath of parent.
    
    Args:
        path: Path to check
        parent: Parent path
        
    Returns:
        True if path is a subpath of parent
        
    Raises:
        FileError: If paths cannot be compared
    """
    try:
        path = normalize_path(path)
        parent = normalize_path(parent)
        return str(path).startswith(str(parent))
    except Exception as e:
        raise FileError(f"Failed to compare paths {path} and {parent}: {str(e)}") from e 