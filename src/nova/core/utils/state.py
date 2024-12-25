"""State management utilities for Nova document processor."""

import json
import gzip
import fcntl
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
from enum import Enum

from ..errors import StateError
from .file_ops import FileOperationsManager
from .logging import get_logger

class ProcessingStatus(Enum):
    """Processing status enumeration."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"

class StateManager:
    """Manager for pipeline state."""
    
    VERSION = "1.0.0"  # State format version
    
    def __init__(self, state_file: Union[str, Path]):
        """Initialize the state manager.
        
        Args:
            state_file: Path to state file
        """
        self.state_file = Path(state_file)
        self.logger = get_logger(__name__)
        self._lock_file = self.state_file.with_suffix('.lock')
        self._backup_file = self.state_file.with_suffix('.bak')
        self._lock_fd = None
        self._file_ops = FileOperationsManager()
        
        self._state: Dict[str, Any] = {
            'version': self.VERSION,
            'file_hashes': {},           # Map of file paths to their hashes
            'processing_status': {},      # Map of file paths to their processing status
            'modification_times': {},     # Map of file paths to their last modification times
            'error_states': {},          # Map of file paths to their error states
            'image_cache': {             # Image cache status
                'hits': 0,
                'misses': 0,
                'errors': 0,
                'entries': {}            # Map of image paths to their cache info
            },
            'api_usage': {               # API usage metrics
                'openai': {
                    'calls': 0,
                    'tokens': 0,
                    'costs': 0.0,
                    'errors': 0
                }
            },
            'conversion_history': [],     # List of conversion operations
            'last_update': None,         # Timestamp of last state update
            'checksum': None             # State data checksum
        }
        self._load_state()
    
    def _acquire_lock(self) -> None:
        """Acquire lock on state file.
        
        Raises:
            StateError: If lock cannot be acquired
        """
        try:
            self._lock_fd = open(self._lock_file, 'w')
            fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (IOError, OSError) as e:
            if self._lock_fd:
                self._lock_fd.close()
            raise StateError(f"Failed to acquire state lock: {str(e)}") from e
    
    def _release_lock(self) -> None:
        """Release lock on state file."""
        if self._lock_fd:
            try:
                fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_UN)
                self._lock_fd.close()
            except (IOError, OSError) as e:
                self.logger.error(f"Failed to release state lock: {str(e)}")
            finally:
                self._lock_fd = None
    
    def _compute_checksum(self, data: Dict[str, Any]) -> str:
        """Compute checksum of state data.
        
        Args:
            data: State data
            
        Returns:
            Checksum string
        """
        # Create copy without checksum field
        data_copy = data.copy()
        data_copy.pop('checksum', None)
        
        # Compute checksum of sorted JSON string
        json_str = json.dumps(data_copy, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def _validate_state(self, data: Dict[str, Any]) -> None:
        """Validate state data.
        
        Args:
            data: State data to validate
            
        Raises:
            StateError: If validation fails
        """
        required_keys = {
            'version', 'file_hashes', 'processing_status', 'modification_times',
            'error_states', 'image_cache', 'api_usage', 'conversion_history',
            'last_update', 'checksum'
        }
        
        # Check required keys
        missing_keys = required_keys - set(data.keys())
        if missing_keys:
            raise StateError(f"Missing required state keys: {missing_keys}")
        
        # Validate version
        if data['version'] != self.VERSION:
            raise StateError(
                f"State version mismatch: expected {self.VERSION}, got {data['version']}"
            )
        
        # Validate checksum
        if data['checksum']:
            computed = self._compute_checksum(data)
            if computed != data['checksum']:
                raise StateError("State checksum validation failed")
    
    def _migrate_state(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate state data to current version.
        
        Args:
            data: State data to migrate
            
        Returns:
            Migrated state data
            
        Raises:
            StateError: If migration fails
        """
        if 'version' not in data:
            # Pre-versioned state
            data['version'] = "0.0.0"
        
        version = data['version']
        if version == self.VERSION:
            return data
            
        self.logger.info(f"Migrating state from version {version} to {self.VERSION}")
        
        try:
            # Perform version-specific migrations here
            if version == "0.0.0":
                # Migrate from pre-versioned state
                data['checksum'] = None
                data['version'] = self.VERSION
            
            return data
            
        except Exception as e:
            raise StateError(f"Failed to migrate state: {str(e)}") from e
    
    async def _backup_state(self) -> None:
        """Create backup of state file."""
        try:
            if await self._file_ops.path_exists(self.state_file):
                await self._file_ops.copy_file(self.state_file, self._backup_file)
        except Exception as e:
            self.logger.error(f"Failed to create state backup: {str(e)}")
    
    async def _load_state(self) -> None:
        """Load state from file.
        
        Raises:
            StateError: If state cannot be loaded
        """
        try:
            self._acquire_lock()
            
            # Create state file if it doesn't exist
            await self._file_ops.create_file(self.state_file)
            
            # Read state file
            try:
                # Try reading as gzip first
                content = await self._file_ops.read_gzipped_file(self.state_file)
            except:
                # Fall back to plain text
                content = await self._file_ops.read_file(self.state_file)
            
            # Parse state
            if content:
                loaded_state = json.loads(content)
                
                # Migrate state if needed
                loaded_state = self._migrate_state(loaded_state)
                
                # Validate state
                self._validate_state(loaded_state)
                
                # Update state while preserving structure
                for key in self._state:
                    if key in loaded_state:
                        self._state[key] = loaded_state[key]
                
        except Exception as e:
            raise StateError(f"Failed to load state: {str(e)}") from e
        finally:
            self._release_lock()
    
    async def _save_state(self) -> None:
        """Save state to file.
        
        Raises:
            StateError: If state cannot be saved
        """
        try:
            self._acquire_lock()
            
            # Update metadata
            self._state['last_update'] = datetime.now().isoformat()
            self._state['checksum'] = self._compute_checksum(self._state)
            
            # Create backup
            await self._backup_state()
            
            # Create state file if it doesn't exist
            await self._file_ops.create_file(self.state_file)
            
            # Write state file (compressed if over 1MB)
            content = json.dumps(self._state, indent=2)
            if len(content.encode()) > 1024 * 1024:
                await self._file_ops.write_gzipped_file(self.state_file, content)
            else:
                await self._file_ops.write_file(self.state_file, content)
            
        except Exception as e:
            raise StateError(f"Failed to save state: {str(e)}") from e
        finally:
            self._release_lock()
    
    def update_file_hash(self, file_path: Union[str, Path]) -> None:
        """Update file hash in state.
        
        Args:
            file_path: Path to file
            
        Raises:
            StateError: If hash cannot be computed or state cannot be saved
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            
            # Compute file hash
            sha256_hash = hashlib.sha256()
            with path.open('rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    sha256_hash.update(chunk)
            
            # Update state
            self._state['file_hashes'][str(path)] = sha256_hash.hexdigest()
            self._state['modification_times'][str(path)] = path.stat().st_mtime
            self._save_state()
            
        except Exception as e:
            raise StateError(f"Failed to update file hash: {str(e)}") from e
    
    def update_processing_status(
        self,
        file_path: Union[str, Path],
        status: ProcessingStatus,
        error: Optional[str] = None
    ) -> None:
        """Update processing status in state.
        
        Args:
            file_path: Path to file
            status: Processing status
            error: Optional error message
            
        Raises:
            StateError: If state cannot be saved
        """
        try:
            path = str(Path(file_path))
            self._state['processing_status'][path] = status.value
            
            if error:
                self._state['error_states'][path] = {
                    'error': error,
                    'timestamp': datetime.now().isoformat()
                }
            elif path in self._state['error_states']:
                del self._state['error_states'][path]
            
            self._save_state()
            
        except Exception as e:
            raise StateError(f"Failed to update processing status: {str(e)}") from e
    
    def update_image_cache_stats(
        self,
        hit: bool = False,
        miss: bool = False,
        error: bool = False,
        image_path: Optional[Union[str, Path]] = None,
        cache_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update image cache statistics.
        
        Args:
            hit: Whether cache was hit
            miss: Whether cache was missed
            error: Whether error occurred
            image_path: Optional path to image
            cache_info: Optional cache entry info
            
        Raises:
            StateError: If state cannot be saved
        """
        try:
            if hit:
                self._state['image_cache']['hits'] += 1
            if miss:
                self._state['image_cache']['misses'] += 1
            if error:
                self._state['image_cache']['errors'] += 1
            
            if image_path and cache_info:
                self._state['image_cache']['entries'][str(Path(image_path))] = {
                    **cache_info,
                    'last_access': datetime.now().isoformat()
                }
            
            self._save_state()
            
        except Exception as e:
            raise StateError(f"Failed to update image cache stats: {str(e)}") from e
    
    def update_api_usage(
        self,
        provider: str,
        calls: int = 0,
        tokens: int = 0,
        costs: float = 0.0,
        error: bool = False
    ) -> None:
        """Update API usage metrics.
        
        Args:
            provider: API provider name
            calls: Number of API calls
            tokens: Number of tokens used
            costs: API costs
            error: Whether error occurred
            
        Raises:
            StateError: If state cannot be saved
        """
        try:
            if provider not in self._state['api_usage']:
                self._state['api_usage'][provider] = {
                    'calls': 0,
                    'tokens': 0,
                    'costs': 0.0,
                    'errors': 0
                }
            
            self._state['api_usage'][provider]['calls'] += calls
            self._state['api_usage'][provider]['tokens'] += tokens
            self._state['api_usage'][provider]['costs'] += costs
            if error:
                self._state['api_usage'][provider]['errors'] += 1
            
            self._save_state()
            
        except Exception as e:
            raise StateError(f"Failed to update API usage: {str(e)}") from e
    
    def add_conversion(
        self,
        source_path: Union[str, Path],
        target_path: Union[str, Path],
        conversion_type: str,
        success: bool,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add conversion operation to history.
        
        Args:
            source_path: Source file path
            target_path: Target file path
            conversion_type: Type of conversion
            success: Whether conversion succeeded
            error: Optional error message
            metadata: Optional conversion metadata
            
        Raises:
            StateError: If state cannot be saved
        """
        try:
            conversion = {
                'source': str(Path(source_path)),
                'target': str(Path(target_path)),
                'type': conversion_type,
                'success': success,
                'timestamp': datetime.now().isoformat()
            }
            
            if error:
                conversion['error'] = error
            if metadata:
                conversion['metadata'] = metadata
            
            self._state['conversion_history'].append(conversion)
            self._save_state()
            
        except Exception as e:
            raise StateError(f"Failed to add conversion: {str(e)}") from e
    
    def get_file_status(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Get comprehensive file status.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dict containing file status information
        """
        path = str(Path(file_path))
        return {
            'hash': self._state['file_hashes'].get(path),
            'status': self._state['processing_status'].get(path),
            'modified': self._state['modification_times'].get(path),
            'error': self._state['error_states'].get(path)
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get image cache statistics.
        
        Returns:
            Dict containing cache statistics
        """
        return self._state['image_cache'].copy()
    
    def get_api_stats(self) -> Dict[str, Any]:
        """Get API usage statistics.
        
        Returns:
            Dict containing API usage statistics
        """
        return self._state['api_usage'].copy()
    
    def get_conversion_history(
        self,
        limit: Optional[int] = None,
        conversion_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get conversion history.
        
        Args:
            limit: Optional limit on number of entries
            conversion_type: Optional filter by conversion type
            
        Returns:
            List of conversion history entries
        """
        history = self._state['conversion_history']
        if conversion_type:
            history = [h for h in history if h['type'] == conversion_type]
        if limit:
            history = history[-limit:]
        return history
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get state value.
        
        Args:
            key: State key
            default: Default value if key not found
            
        Returns:
            State value
        """
        return self._state.get(key, default)
    
    def set_state(self, key: str, value: Any) -> None:
        """Set state value.
        
        Args:
            key: State key
            value: State value
            
        Raises:
            StateError: If state cannot be saved
        """
        try:
            self._state[key] = value
            self._save_state()
        except Exception as e:
            raise StateError(f"Failed to set state: {str(e)}") from e
    
    def update_state(self, values: Dict[str, Any]) -> None:
        """Update multiple state values.
        
        Args:
            values: Dict of state key-value pairs
            
        Raises:
            StateError: If state cannot be saved
        """
        try:
            self._state.update(values)
            self._save_state()
        except Exception as e:
            raise StateError(f"Failed to update state: {str(e)}") from e
    
    def clear_state(self) -> None:
        """Clear all state.
        
        Raises:
            StateError: If state cannot be saved
        """
        try:
            self._state = {
                'file_hashes': {},
                'processing_status': {},
                'modification_times': {},
                'error_states': {},
                'image_cache': {
                    'hits': 0,
                    'misses': 0,
                    'errors': 0,
                    'entries': {}
                },
                'api_usage': {},
                'conversion_history': [],
                'last_update': None
            }
            self._save_state()
        except Exception as e:
            raise StateError(f"Failed to clear state: {str(e)}") from e
    
    def get_all_state(self) -> Dict[str, Any]:
        """Get all state values.
        
        Returns:
            Dict of all state key-value pairs
        """
        return self._state.copy()
    
    def has_state(self, key: str) -> bool:
        """Check if state key exists.
        
        Args:
            key: State key
            
        Returns:
            True if key exists
        """
        return key in self._state 