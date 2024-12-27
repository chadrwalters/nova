"""File state tracking for caching system."""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Set, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class FileState:
    """State information for a single file."""
    file_path: str
    content_hash: str
    mod_time: float
    size: int
    dependencies: Set[str]
    last_processed: float
    metadata: Dict[str, Any]

    @classmethod
    def from_file(cls, file_path: str, dependencies: Optional[Set[str]] = None) -> 'FileState':
        """Create FileState from a file.
        
        Args:
            file_path: Path to the file
            dependencies: Optional set of dependency file paths
            
        Returns:
            FileState instance
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        # Calculate file hash
        hasher = hashlib.sha256()
        with path.open('rb') as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
                
        stat = path.stat()
        
        return cls(
            file_path=str(path),
            content_hash=hasher.hexdigest(),
            mod_time=stat.st_mtime,
            size=stat.st_size,
            dependencies=dependencies or set(),
            last_processed=datetime.now().timestamp(),
            metadata={}
        )


class FileStateManager:
    """Manages file state tracking for the caching system."""
    
    def __init__(self, state_file: str = '.file_state.json'):
        """Initialize FileStateManager.
        
        Args:
            state_file: Path to state storage file
        """
        self.state_file = Path(state_file)
        self.states: Dict[str, FileState] = {}
        self._load_state()
        
    def _load_state(self) -> None:
        """Load state from file."""
        if not self.state_file.exists():
            return
            
        try:
            with self.state_file.open('r') as f:
                data = json.load(f)
                
            for file_path, state_dict in data.items():
                # Convert dependencies back to set
                state_dict['dependencies'] = set(state_dict['dependencies'])
                self.states[file_path] = FileState(**state_dict)
        except Exception as e:
            # Log error but continue with empty state
            print(f"Error loading state file: {e}")
            
    def _save_state(self) -> None:
        """Save state to file."""
        try:
            # Convert to dict format for JSON
            data = {
                path: asdict(state) for path, state in self.states.items()
            }
            
            # Ensure directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write atomically using temporary file
            temp_file = self.state_file.with_suffix('.tmp')
            with temp_file.open('w') as f:
                json.dump(data, f, indent=2)
                
            # Atomic rename
            temp_file.replace(self.state_file)
        except Exception as e:
            print(f"Error saving state file: {e}")
            
    def get_file_state(self, file_path: str) -> Optional[FileState]:
        """Get state for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            FileState if exists, None otherwise
        """
        return self.states.get(str(Path(file_path)))
        
    def update_file_state(self, file_path: str, dependencies: Optional[Set[str]] = None) -> FileState:
        """Update state for a file.
        
        Args:
            file_path: Path to the file
            dependencies: Optional set of dependency file paths
            
        Returns:
            Updated FileState
        """
        state = FileState.from_file(file_path, dependencies)
        self.states[str(Path(file_path))] = state
        self._save_state()
        return state
        
    def has_changed(self, file_path: str) -> bool:
        """Check if a file has changed since last tracked.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file has changed or wasn't tracked
        """
        path = Path(file_path)
        if not path.exists():
            return True
            
        current_state = self.get_file_state(file_path)
        if not current_state:
            return True
            
        try:
            new_state = FileState.from_file(file_path, current_state.dependencies)
            
            # Check if file or any dependencies changed
            if new_state.content_hash != current_state.content_hash:
                return True
                
            if new_state.mod_time != current_state.mod_time:
                return True
                
            for dep in current_state.dependencies:
                if self.has_changed(dep):
                    return True
                    
            return False
        except Exception:
            # If any error occurs, assume file changed
            return True
            
    def add_dependency(self, file_path: str, dependency: str) -> None:
        """Add a dependency for a file.
        
        Args:
            file_path: Path to the file
            dependency: Path to the dependency file
        """
        state = self.get_file_state(file_path)
        if state:
            state.dependencies.add(str(Path(dependency)))
            self._save_state()
            
    def remove_dependency(self, file_path: str, dependency: str) -> None:
        """Remove a dependency for a file.
        
        Args:
            file_path: Path to the file
            dependency: Path to the dependency file
        """
        state = self.get_file_state(file_path)
        if state:
            state.dependencies.discard(str(Path(dependency)))
            self._save_state()
            
    def get_dependencies(self, file_path: str) -> Set[str]:
        """Get dependencies for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Set of dependency file paths
        """
        state = self.get_file_state(file_path)
        return state.dependencies if state else set()
        
    def clear_state(self) -> None:
        """Clear all state information."""
        self.states.clear()
        self._save_state()
        
    def remove_file(self, file_path: str) -> None:
        """Remove state for a file.
        
        Args:
            file_path: Path to the file
        """
        self.states.pop(str(Path(file_path)), None)
        self._save_state()
        
    def update_metadata(self, file_path: str, metadata: Dict[str, Any]) -> None:
        """Update metadata for a file.
        
        Args:
            file_path: Path to the file
            metadata: Metadata to update
        """
        state = self.get_file_state(file_path)
        if state:
            state.metadata.update(metadata)
            self._save_state() 