"""File operations utilities for Nova."""

import os
import shutil
import asyncio
import aiofiles
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union, List, Set
from datetime import datetime
from functools import wraps
import time
import psutil
import json

from ..errors import FileOperationError
from ..logging import get_logger

def monitor_performance(operation_name: str):
    """Decorator to monitor performance of file operations.
    
    Args:
        operation_name: Name of the operation being monitored
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss
            
            try:
                result = await func(self, *args, **kwargs)
                success = True
            except Exception as e:
                success = False
                raise
            finally:
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss
                
                # Update metrics
                elapsed = end_time - start_time
                memory_used = end_memory - start_memory
                
                metrics = {
                    'timestamp': datetime.now().isoformat(),
                    'operation': operation_name,
                    'success': success,
                    'elapsed_seconds': elapsed,
                    'memory_bytes': memory_used,
                    'args': str(args),
                    'kwargs': str(kwargs)
                }
                
                # Update performance metrics
                await self._update_metrics(metrics)
            
            return result
        return wrapper
    return decorator

class FileOperationsManager:
    """Manager for file operations with both sync and async support."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize file operations manager.
        
        Args:
            config: Optional configuration dictionary
        """
        self.logger = get_logger(__name__)
        
        # Load configuration
        self.config = {
            'retry': {
                'max_attempts': 3,
                'delay_seconds': 1,
                'backoff_factor': 2
            },
            'performance': {
                'metrics_enabled': True,
                'log_threshold_seconds': 5.0,
                'memory_threshold_mb': 100,
                'metrics_retention_days': 7
            },
            'validation': {
                'verify_copies': True,
                'verify_moves': True,
                'check_permissions': True
            }
        }
        if config:
            self.config.update(config)
        
        # Initialize metrics
        self.metrics = {
            'operations': {
                'copies': 0,
                'moves': 0,
                'deletes': 0,
                'temp_files': 0
            },
            'errors': {
                'copy_errors': 0,
                'move_errors': 0,
                'delete_errors': 0,
                'permission_errors': 0
            },
            'timing': {
                'total_time': 0,
                'avg_time': 0,
                'slowest_op': 0,
                'fastest_op': float('inf')
            },
            'retries': {
                'total_retries': 0,
                'successful_retries': 0,
                'failed_retries': 0
            },
            'history': []  # Limited list of recent operations
        }
        
        # Track resource state
        self._initialized = False
        self._cleanup_required = False
        self._temp_files: Set[Path] = set()
        self._active_operations = 0
        self._lock = asyncio.Lock()

    async def _track_operation(self) -> None:
        """Track an active operation."""
        async with self._lock:
            self._active_operations += 1
    
    async def _complete_operation(self) -> None:
        """Complete an active operation."""
        async with self._lock:
            self._active_operations -= 1
    
    def _add_temp_file(self, file_path: Path) -> None:
        """Track a temporary file for cleanup.
        
        Args:
            file_path: Path to temporary file
        """
        self._temp_files.add(file_path)
    
    async def __aenter__(self) -> 'FileOperationsManager':
        """Enter async context and initialize resources.
        
        Returns:
            self: The FileOperationsManager instance
            
        Raises:
            FileOperationError: If initialization fails
        """
        if self._initialized:
            self.logger.warning("FileOperationsManager already initialized")
            return self
            
        try:
            # Create any required directories
            if self.config['performance']['metrics_enabled']:
                metrics_dir = Path("metrics")
                metrics_dir.mkdir(parents=True, exist_ok=True)
            
            self._initialized = True
            self._cleanup_required = True
            
            self.logger.debug("FileOperationsManager initialized successfully")
            return self
            
        except Exception as e:
            self.logger.error(f"Failed to initialize FileOperationsManager: {str(e)}")
            # Clean up any partially initialized resources
            await self.__aexit__(type(e), e, e.__traceback__)
            raise FileOperationError(f"Failed to initialize FileOperationsManager: {str(e)}")
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context and clean up resources.
        
        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred
        """
        if not self._cleanup_required:
            return
            
        try:
            # Wait for active operations to complete
            if self._active_operations > 0:
                self.logger.warning(f"Waiting for {self._active_operations} active operations to complete")
                async with self._lock:
                    while self._active_operations > 0:
                        await asyncio.sleep(0.1)
            
            # Clean up temporary files
            for temp_file in self._temp_files:
                try:
                    if temp_file.exists():
                        await self.delete_file(temp_file, missing_ok=True)
                except Exception as e:
                    self.logger.error(f"Error cleaning up temporary file {temp_file}: {str(e)}")
            
            self._initialized = False
            self._cleanup_required = False
            self._temp_files.clear()
            self._active_operations = 0
            
            self.logger.debug("FileOperationsManager cleanup completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during FileOperationsManager cleanup: {str(e)}")
            if exc_type is None:
                raise FileOperationError(f"Error during FileOperationsManager cleanup: {str(e)}")
    
    async def create_temp_file(self, suffix: Optional[str] = None, prefix: Optional[str] = None) -> Path:
        """Create a temporary file that will be automatically cleaned up.
        
        Args:
            suffix: Optional file suffix
            prefix: Optional file prefix
            
        Returns:
            Path to temporary file
            
        Raises:
            FileOperationError: If creation fails
        """
        if not self._initialized:
            raise FileOperationError("FileOperationsManager not initialized. Use async with context.")
            
        await self._track_operation()
        try:
            self.metrics['operations']['temp_files'] += 1
            
            # Create temp file
            temp_fd, temp_path = await asyncio.to_thread(
                os.mkstemp,
                suffix=suffix,
                prefix=prefix
            )
            os.close(temp_fd)
            
            temp_path = Path(temp_path)
            self._add_temp_file(temp_path)
            return temp_path
            
        except Exception as e:
            raise FileOperationError(f"Failed to create temporary file: {str(e)}") from e
        finally:
            await self._complete_operation()
    
    async def _update_metrics(self, operation_metrics: Dict[str, Any]) -> None:
        """Update performance metrics with new operation data.
        
        Args:
            operation_metrics: Metrics from a single operation
        """
        if not self.config['performance']['metrics_enabled']:
            return
        
        try:
            # Update operation counts
            op_type = operation_metrics['operation']
            self.metrics['operations'][f"{op_type}s"] = self.metrics['operations'].get(f"{op_type}s", 0) + 1
            
            # Update timing metrics
            elapsed = operation_metrics['elapsed_seconds']
            self.metrics['timing']['total_time'] += elapsed
            total_ops = sum(self.metrics['operations'].values())
            self.metrics['timing']['avg_time'] = (
                self.metrics['timing']['total_time'] / total_ops if total_ops > 0 else 0
            )
            self.metrics['timing']['slowest_op'] = max(
                self.metrics['timing']['slowest_op'],
                elapsed
            )
            self.metrics['timing']['fastest_op'] = min(
                self.metrics['timing']['fastest_op'],
                elapsed
            )
            
            # Add to history (keep last 1000 operations)
            self.metrics['history'].append(operation_metrics)
            self.metrics['history'] = self.metrics['history'][-1000:]
            
            # Check for alerts
            if elapsed > self.config['performance']['log_threshold_seconds']:
                self.logger.warning(
                    f"Slow operation detected: {op_type} took {elapsed:.2f} seconds "
                    f"(threshold: {self.config['performance']['log_threshold_seconds']} seconds)"
                )
            
            memory_mb = operation_metrics['memory_bytes'] / (1024 * 1024)
            if memory_mb > self.config['performance']['memory_threshold_mb']:
                self.logger.warning(
                    f"High memory usage detected: {op_type} used {memory_mb:.1f}MB "
                    f"(threshold: {self.config['performance']['memory_threshold_mb']}MB)"
                )
            
        except Exception as e:
            self.logger.error(f"Error updating metrics: {str(e)}")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate a performance report.
        
        Returns:
            Dictionary containing performance statistics
        """
        total_ops = sum(self.metrics['operations'].values())
        total_errors = sum(self.metrics['errors'].values())
        
        return {
            'summary': {
                'total_operations': total_ops,
                'total_errors': total_errors,
                'error_rate': (total_errors / total_ops) if total_ops > 0 else 0,
                'avg_operation_time': self.metrics['timing']['avg_time'],
                'retry_success_rate': (
                    self.metrics['retries']['successful_retries'] / 
                    self.metrics['retries']['total_retries']
                ) if self.metrics['retries']['total_retries'] > 0 else 0
            },
            'operations': self.metrics['operations'],
            'errors': self.metrics['errors'],
            'timing': {
                k: v for k, v in self.metrics['timing'].items()
                if k != 'total_time'  # Exclude raw total
            },
            'retries': self.metrics['retries']
        }
    
    async def _retry_operation(self, operation: callable, *args, **kwargs) -> Any:
        """Retry an operation with exponential backoff.
        
        Args:
            operation: Function to retry
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Result of the operation
            
        Raises:
            FileOperationError: If all retries fail
        """
        max_attempts = self.config['retry']['max_attempts']
        delay = self.config['retry']['delay_seconds']
        backoff = self.config['retry']['backoff_factor']
        
        last_error = None
        self.metrics['retries']['total_retries'] += 1
        
        for attempt in range(max_attempts):
            try:
                result = await operation(*args, **kwargs)
                if attempt > 0:
                    self.metrics['retries']['successful_retries'] += 1
                return result
            except Exception as e:
                last_error = e
                if attempt < max_attempts - 1:
                    wait_time = delay * (backoff ** attempt)
                    self.logger.warning(
                        f"Operation failed (attempt {attempt + 1}/{max_attempts}), "
                        f"retrying in {wait_time:.1f}s: {str(e)}"
                    )
                    await asyncio.sleep(wait_time)
        
        self.metrics['retries']['failed_retries'] += 1
        raise FileOperationError(f"Operation failed after {max_attempts} attempts: {str(last_error)}")
    
    async def _verify_operation(self, src: Path, dst: Path, operation: str) -> None:
        """Verify a file operation was successful.
        
        Args:
            src: Source path
            dst: Destination path
            operation: Operation type ('copy' or 'move')
            
        Raises:
            FileOperationError: If verification fails
        """
        if not dst.exists():
            raise FileOperationError(f"Destination file does not exist after {operation}: {dst}")
        
        if operation == 'copy':
            if not src.exists():
                raise FileOperationError(f"Source file no longer exists after copy: {src}")
            if src.stat().st_size != dst.stat().st_size:
                raise FileOperationError(
                    f"Size mismatch after copy: {src.stat().st_size} != {dst.stat().st_size}"
                )
        elif operation == 'move':
            if src.exists():
                raise FileOperationError(f"Source file still exists after move: {src}")
    
    @monitor_performance('copy')
    async def copy_file(self, src: Union[str, Path], dst: Union[str, Path], overwrite: bool = False) -> None:
        """Copy a file with retry and verification.
        
        Args:
            src: Source file path
            dst: Destination file path
            overwrite: Whether to overwrite existing files
            
        Raises:
            FileOperationError: If copy fails or manager not initialized
        """
        if not self._initialized:
            raise FileOperationError("FileOperationsManager not initialized. Use async with context.")
            
        await self._track_operation()
        try:
            src_path = Path(src)
            dst_path = Path(dst)
            
            # Validate paths
            if not src_path.exists():
                raise FileOperationError(f"Source file does not exist: {src_path}")
            if dst_path.exists() and not overwrite:
                raise FileOperationError(f"Destination file already exists: {dst_path}")
            
            # Create destination directory if needed
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file with retry
            async def _do_copy():
                # Use shutil for large files, aiofiles for small files
                if src_path.stat().st_size > 10 * 1024 * 1024:  # 10MB
                    await asyncio.to_thread(shutil.copy2, src_path, dst_path)
                else:
                    async with aiofiles.open(src_path, 'rb') as fsrc:
                        async with aiofiles.open(dst_path, 'wb') as fdst:
                            await fdst.write(await fsrc.read())
            
            await self._retry_operation(_do_copy)
            
            # Verify copy if configured
            if self.config['validation']['verify_copies']:
                await self._verify_operation(src_path, dst_path, 'copy')
            
        except Exception as e:
            self.metrics['errors']['copy_errors'] += 1
            raise FileOperationError(f"Failed to copy file: {str(e)}") from e
        finally:
            await self._complete_operation()
    
    @monitor_performance('move')
    async def move_file(self, src: Union[str, Path], dst: Union[str, Path], overwrite: bool = False) -> None:
        """Move a file with retry and verification.
        
        Args:
            src: Source file path
            dst: Destination file path
            overwrite: Whether to overwrite existing files
            
        Raises:
            FileOperationError: If move fails or manager not initialized
        """
        if not self._initialized:
            raise FileOperationError("FileOperationsManager not initialized. Use async with context.")
            
        await self._track_operation()
        try:
            src_path = Path(src)
            dst_path = Path(dst)
            
            # Validate paths
            if not src_path.exists():
                raise FileOperationError(f"Source file does not exist: {src_path}")
            if dst_path.exists() and not overwrite:
                raise FileOperationError(f"Destination file already exists: {dst_path}")
            
            # Create destination directory if needed
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file with retry
            async def _do_move():
                await asyncio.to_thread(shutil.move, src_path, dst_path)
            
            await self._retry_operation(_do_move)
            
            # Verify move if configured
            if self.config['validation']['verify_moves']:
                await self._verify_operation(src_path, dst_path, 'move')
            
        except Exception as e:
            self.metrics['errors']['move_errors'] += 1
            raise FileOperationError(f"Failed to move file: {str(e)}") from e
        finally:
            await self._complete_operation()
    
    @monitor_performance('delete')
    async def delete_file(self, path: Union[str, Path], missing_ok: bool = False) -> None:
        """Delete a file with retry.
        
        Args:
            path: Path to file to delete
            missing_ok: Whether to ignore missing files
            
        Raises:
            FileOperationError: If deletion fails or manager not initialized
        """
        if not self._initialized:
            raise FileOperationError("FileOperationsManager not initialized. Use async with context.")
            
        await self._track_operation()
        try:
            file_path = Path(path)
            
            if not file_path.exists():
                if missing_ok:
                    return
                raise FileOperationError(f"File does not exist: {file_path}")
            
            # Delete file with retry
            async def _do_delete():
                await asyncio.to_thread(os.remove, file_path)
            
            await self._retry_operation(_do_delete)
            
            # Verify deletion
            if file_path.exists():
                raise FileOperationError(f"File still exists after deletion: {file_path}")
            
        except Exception as e:
            self.metrics['errors']['delete_errors'] += 1
            raise FileOperationError(f"Failed to delete file: {str(e)}") from e
        finally:
            await self._complete_operation()
    
    async def cleanup_temp_files(self) -> None:
        """Clean up any remaining temporary files."""
        # Add cleanup logic here if needed
        pass
    
    async def cleanup_temp_files(self) -> None:
        """Clean up any remaining temporary files."""
        # Add cleanup logic here if needed
        pass
    
    async def path_exists(self, path: Union[str, Path]) -> bool:
        """Check if a path exists.
        
        Args:
            path: Path to check
            
        Returns:
            True if path exists, False otherwise
        """
        if not self._initialized:
            raise FileOperationError("FileOperationsManager not initialized. Use async with context.")
        
        await self._track_operation()
        try:
            path = Path(path)
            exists = path.exists()
            return exists
        finally:
            await self._complete_operation()
            
    async def remove_file(self, path: Union[str, Path]) -> None:
        """Remove a file.
        
        Args:
            path: Path to file to remove
        """
        if not self._initialized:
            raise FileOperationError("FileOperationsManager not initialized. Use async with context.")
        
        await self._track_operation()
        try:
            path = Path(path)
            if path.exists():
                path.unlink()
                self.metrics['operations']['deletes'] += 1
        except Exception as e:
            self.metrics['errors']['delete_errors'] += 1
            raise FileOperationError(f"Failed to remove file {path}: {str(e)}") from e
        finally:
            await self._complete_operation()
    
    async def _save_to_cache(self, cache_key: str, content: str) -> None:
        """Save content to cache.
        
        Args:
            cache_key: Cache key to save under
            content: Content to cache
        """
        cache_file = self.pipeline_config.paths.cache_dir / f"{cache_key}.json"
        cache_data = {
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        async with aiofiles.open(cache_file, 'w') as f:
            await f.write(json.dumps(cache_data))

    @monitor_performance('read_file')
    async def read_file(self, file_path: Union[str, Path]) -> str:
        """Read the contents of a file.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            Contents of the file as a string
            
        Raises:
            FileOperationError: If reading fails
        """
        if not self._initialized:
            raise FileOperationError("FileOperationsManager not initialized. Use async with context.")
            
        await self._track_operation()
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                return await f.read()
        except Exception as e:
            raise FileOperationError(f"Failed to read file {file_path}: {str(e)}") from e
        finally:
            await self._complete_operation() 