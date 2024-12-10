"""Resource management for file operations and cleanup."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Optional, Set
import aiofiles
import aiofiles.os as aos
import psutil
import tempfile
from dataclasses import dataclass
import asyncio
import fcntl
import structlog

from src.core.exceptions import ResourceError

logger = structlog.get_logger(__name__)

@dataclass
class ResourceLimits:
    """Resource limits for processing."""
    max_memory_percent: float = 80.0
    max_temp_size_mb: int = 1000
    max_open_files: int = 100

class ResourceManager:
    """Manages resources during document processing."""
    
    def __init__(self, resource_limits: Optional[ResourceLimits] = None):
        """Initialize resource manager with optional limits.
        
        Args:
            resource_limits: Optional resource limits configuration
        """
        self.limits = resource_limits or ResourceLimits()
        self.temp_files: Set[Path] = set()
        self.locks: dict[Path, asyncio.Lock] = {}
        self.logger = logger.bind(component="resource_manager")
        
    async def check_resources(self) -> None:
        """
        Checks if system resources are within acceptable limits.

        Raises:
            ResourceError: If resource limits are exceeded
        """
        memory = psutil.virtual_memory()
        if memory.percent > self.limits.max_memory_percent:
            raise ResourceError(
                f"Memory usage exceeds limit: {memory.percent}%",
                resource_type="memory"
            )

        temp_size = await self._get_temp_size()
        if temp_size > self.limits.max_temp_size_mb * 1024 * 1024:
            raise ResourceError(
                f"Temporary storage exceeds limit: {temp_size / (1024*1024):.2f}MB",
                resource_type="storage"
            )

    @asynccontextmanager
    async def temp_file(self, suffix: str = "") -> AsyncGenerator[Path, None]:
        """Creates and manages a temporary file.
        
        Args:
            suffix: Optional file suffix
            
        Yields:
            Path to temporary file
            
        Raises:
            ResourceError: If file operations fail
        """
        temp_path = Path(tempfile.mktemp(suffix=suffix))
        self.temp_files.add(temp_path)
        
        try:
            await aos.makedirs(temp_path.parent, exist_ok=True)
            async with aiofiles.open(temp_path, 'w') as f:
                await f.write("")
            yield temp_path
        except Exception as e:
            raise ResourceError(
                f"Failed to create temporary file: {e}",
                resource_type="file",
                resource_path=str(temp_path)
            )
        finally:
            try:
                if await aos.path.exists(temp_path):
                    await aos.remove(temp_path)
                self.temp_files.remove(temp_path)
            except Exception as e:
                self.logger.error(
                    "Failed to cleanup temp file",
                    path=str(temp_path),
                    error=str(e)
                )

    @asynccontextmanager
    async def file_lock(self, file_path: Path) -> AsyncGenerator[None, None]:
        """Provides file locking mechanism.
        
        Args:
            file_path: Path to file to lock
            
        Yields:
            None
            
        Raises:
            ResourceError: If locking fails
        """
        if file_path not in self.locks:
            self.locks[file_path] = asyncio.Lock()
            
        async with self.locks[file_path]:
            try:
                async with aiofiles.open(file_path, 'r+b') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    try:
                        yield
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except BlockingIOError:
                raise ResourceError(
                    f"File {file_path} is locked by another process",
                    resource_type="lock",
                    resource_path=str(file_path)
                )

    async def ensure_dir(self, path: Path) -> None:
        """Ensures a directory exists.
        
        Args:
            path: Directory path
            
        Raises:
            ResourceError: If directory creation fails
        """
        try:
            await aos.makedirs(path, exist_ok=True)
        except Exception as e:
            raise ResourceError(
                f"Failed to create directory: {e}",
                resource_type="directory",
                resource_path=str(path)
            )

    async def copy_file(self, src: Path, dst: Path) -> None:
        """Copies a file with proper error handling.
        
        Args:
            src: Source path
            dst: Destination path
            
        Raises:
            ResourceError: If copy operation fails
        """
        try:
            async with aiofiles.open(src, 'rb') as fsrc:
                async with aiofiles.open(dst, 'wb') as fdst:
                    await fdst.write(await fsrc.read())
        except Exception as e:
            raise ResourceError(
                f"Failed to copy file: {e}",
                resource_type="file",
                resource_path=f"{src} -> {dst}"
            )

    async def cleanup(self) -> None:
        """Cleans up all temporary resources."""
        for path in self.temp_files.copy():
            try:
                if await aos.path.exists(path):
                    if await aos.path.isfile(path):
                        await aos.remove(path)
                    elif await aos.path.isdir(path):
                        await aos.removedirs(path)
                self.temp_files.remove(path)
            except Exception as e:
                self.logger.error(
                    "Failed to cleanup resource",
                    path=str(path),
                    error=str(e)
                )

    async def _get_temp_size(self) -> int:
        """
        Calculates total size of temporary files.
        
        Returns:
            Total size in bytes
        """
        total_size = 0
        for path in self.temp_files:
            try:
                if await aos.path.exists(path):
                    stat = await aos.stat(path)
                    total_size += stat.st_size
            except Exception as e:
                self.logger.error(
                    "Failed to get temp file size",
                    path=str(path),
                    error=str(e)
                )
        return total_size

    async def __aenter__(self) -> "ResourceManager":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit with cleanup."""
        await self.cleanup() 