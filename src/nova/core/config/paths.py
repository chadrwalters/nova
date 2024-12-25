"""Path configuration for Nova."""

import os
import stat
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, field_validator

from nova.core.utils.logging import get_logger
from nova.core.errors import ConfigurationError, StateError
from nova.core.utils.file_ops import FileOperationsManager

class DirectoryConfig(BaseModel):
    """Configuration for a directory."""
    path: Path
    required: bool = True
    permissions: int = 0o755
    max_size_mb: Optional[int] = None
    cleanup_policy: Optional[str] = None  # none, age, size
    cleanup_age_days: Optional[int] = None
    cleanup_min_free_mb: Optional[int] = None

class NovaPaths(BaseModel):
    """Configuration for Nova paths."""
    
    # Base directories
    base_dir: DirectoryConfig = Field(
        ...,
        description="Base directory for all Nova operations"
    )
    input_dir: DirectoryConfig = Field(
        ...,
        description="Input directory for documents"
    )
    output_dir: DirectoryConfig = Field(
        ...,
        description="Output directory for processed documents"
    )
    processing_dir: DirectoryConfig = Field(
        ...,
        description="Directory for intermediate processing"
    )
    temp_dir: DirectoryConfig = Field(
        ...,
        description="Directory for temporary files",
        cleanup_policy="age",
        cleanup_age_days=1
    )
    state_dir: DirectoryConfig = Field(
        ...,
        description="Directory for state files",
        permissions=0o700  # Restricted permissions for state files
    )
    
    # Phase directories
    phase_dirs: Dict[str, DirectoryConfig] = Field(
        default_factory=dict,
        description="Phase-specific directories"
    )
    
    # Image directories
    image_dirs: Dict[str, DirectoryConfig] = Field(
        default_factory=dict,
        description="Image processing directories"
    )
    
    # Office directories
    office_dirs: Dict[str, DirectoryConfig] = Field(
        default_factory=dict,
        description="Office document processing directories"
    )
    
    def __init__(self, **data):
        """Initialize NovaPaths with FileOperationsManager."""
        super().__init__(**data)
        self._file_ops = FileOperationsManager()
        self.logger = get_logger(__name__)
    
    @field_validator('*')
    def validate_path(cls, v):
        """Validate environment variables in paths."""
        if isinstance(v, DirectoryConfig):
            path_str = str(v.path)
            if '$' in path_str:
                var_name = path_str[path_str.find('$')+1:]
                if var_name not in os.environ:
                    raise ConfigurationError(f"Environment variable not set: {var_name}")
                v.path = Path(os.path.expandvars(path_str))
        return v
    
    async def get_directory_size(self, dir_path: Path) -> int:
        """Get directory size in bytes.
        
        Args:
            dir_path: Directory path
            
        Returns:
            Directory size in bytes
        """
        total = 0
        try:
            async for entry in self._file_ops.scan_directory(dir_path, recursive=True):
                if await self._file_ops.is_file(entry):
                    stats = await self._file_ops.get_file_stats(entry)
                    total += stats.st_size
        except OSError as e:
            self.logger.error(f"Failed to get size of {dir_path}: {e}")
        return total
    
    async def enforce_size_limit(self, config: DirectoryConfig) -> None:
        """Enforce directory size limit.
        
        Args:
            config: Directory configuration
            
        Raises:
            StateError: If size limit cannot be enforced
        """
        if not config.max_size_mb:
            return
            
        size_bytes = await self.get_directory_size(config.path)
        max_bytes = config.max_size_mb * 1024 * 1024
        
        if size_bytes > max_bytes:
            self.logger.warning(
                f"Directory {config.path} exceeds size limit "
                f"({size_bytes/1024/1024:.1f}MB > {config.max_size_mb}MB)"
            )
            
            if config.cleanup_policy == "size":
                # Delete oldest files until under limit
                files = []
                async for entry in self._file_ops.scan_directory(config.path, recursive=True):
                    if await self._file_ops.is_file(entry):
                        stats = await self._file_ops.get_file_stats(entry)
                        files.append((entry, stats.st_mtime))
                
                files.sort(key=lambda x: x[1])  # Sort by modification time
                
                for file_path, _ in files:
                    if await self._file_ops.is_file(file_path):
                        stats = await self._file_ops.get_file_stats(file_path)
                        await self._file_ops.remove_file(file_path)
                        size_bytes -= stats.st_size
                        if size_bytes <= max_bytes:
                            break
    
    async def cleanup_by_age(self, config: DirectoryConfig) -> None:
        """Clean up old files.
        
        Args:
            config: Directory configuration
        """
        if not config.cleanup_age_days:
            return
            
        cutoff = datetime.now() - timedelta(days=config.cleanup_age_days)
        
        try:
            async for entry in self._file_ops.scan_directory(config.path, recursive=True):
                if await self._file_ops.is_file(entry):
                    stats = await self._file_ops.get_file_stats(entry)
                    mtime = datetime.fromtimestamp(stats.st_mtime)
                    if mtime < cutoff:
                        await self._file_ops.remove_file(entry)
        except OSError as e:
            self.logger.error(f"Failed to clean up old files in {config.path}: {e}")
    
    async def enforce_min_free_space(self, config: DirectoryConfig) -> None:
        """Enforce minimum free space requirement.
        
        Args:
            config: Directory configuration
        """
        if not config.cleanup_min_free_mb:
            return
            
        try:
            stats = await self._file_ops.get_disk_usage(config.path)
            free_mb = stats.free / 1024 / 1024
            
            if free_mb < config.cleanup_min_free_mb:
                self.logger.warning(
                    f"Low disk space on {config.path} "
                    f"({free_mb:.1f}MB < {config.cleanup_min_free_mb}MB)"
                )
                
                if config.cleanup_policy == "size":
                    # Delete oldest files until enough space
                    files = []
                    async for entry in self._file_ops.scan_directory(config.path, recursive=True):
                        if await self._file_ops.is_file(entry):
                            stats = await self._file_ops.get_file_stats(entry)
                            files.append((entry, stats.st_mtime))
                    
                    files.sort(key=lambda x: x[1])  # Sort by modification time
                    
                    for file_path, _ in files:
                        if await self._file_ops.is_file(file_path):
                            await self._file_ops.remove_file(file_path)
                            stats = await self._file_ops.get_disk_usage(config.path)
                            if stats.free / 1024 / 1024 >= config.cleanup_min_free_mb:
                                break
        except OSError as e:
            self.logger.error(f"Failed to check disk space on {config.path}: {e}")
    
    async def verify_directory(self, config: DirectoryConfig) -> None:
        """Verify a directory exists and has correct configuration.
        
        Args:
            config: Directory configuration
            
        Raises:
            ConfigurationError: If directory verification fails
            StateError: If directory operations fail
        """
        try:
            # Create if needed
            if not await self._file_ops.path_exists(config.path):
                if not config.required:
                    return
                self.logger.info(f"Creating directory: {config.path}")
                await self._file_ops.create_directory(config.path)
            
            if not await self._file_ops.is_directory(config.path):
                raise ConfigurationError(
                    f"Path exists but is not a directory: {config.path}"
                )
            
            # Set permissions
            stats = await self._file_ops.get_file_stats(config.path)
            current_mode = stat.S_IMODE(stats.st_mode)
            if current_mode != config.permissions:
                self.logger.info(
                    f"Setting permissions {oct(config.permissions)} on: {config.path}"
                )
                await self._file_ops.set_permissions(config.path, config.permissions)
            
            # Verify writability
            if not await self._file_ops.is_writable(config.path):
                raise ConfigurationError(f"Directory is not writable: {config.path}")
            
            # Enforce size limits
            await self.enforce_size_limit(config)
            
            # Clean up old files
            if config.cleanup_policy == "age":
                await self.cleanup_by_age(config)
            
            # Check free space
            await self.enforce_min_free_space(config)
                
        except (OSError, PermissionError) as e:
            raise StateError(f"Failed to verify/create directory {config.path}: {e}")
    
    async def create_directories(self) -> None:
        """Create and verify all required directories."""
        try:
            # Create and verify base directories
            for name, config in {
                'base_dir': self.base_dir,
                'input_dir': self.input_dir,
                'output_dir': self.output_dir,
                'processing_dir': self.processing_dir,
                'temp_dir': self.temp_dir,
                'state_dir': self.state_dir
            }.items():
                self.logger.info(f"Verifying {name}: {config.path}")
                await self.verify_directory(config)
            
            # Create and verify phase directories
            for name, config in self.phase_dirs.items():
                self.logger.info(f"Verifying phase directory {name}: {config.path}")
                await self.verify_directory(config)
            
            # Create and verify image directories
            for name, config in self.image_dirs.items():
                self.logger.info(f"Verifying image directory {name}: {config.path}")
                await self.verify_directory(config)
            
            # Create and verify office directories
            for name, config in self.office_dirs.items():
                self.logger.info(f"Verifying office directory {name}: {config.path}")
                await self.verify_directory(config)
                
        except Exception as e:
            raise ConfigurationError(f"Failed to create directories: {str(e)}") 