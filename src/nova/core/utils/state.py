"""State management utilities for Nova document processor."""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Union

from ..errors import StateError
from .paths import ensure_file

class StateManager:
    """Manager for pipeline state."""
    
    def __init__(self, state_file: Union[str, Path]):
        """Initialize the state manager.
        
        Args:
            state_file: Path to state file
        """
        self.state_file = Path(state_file)
        self._state: Dict[str, Any] = {}
        self._load_state()
    
    def _load_state(self) -> None:
        """Load state from file.
        
        Raises:
            StateError: If state cannot be loaded
        """
        try:
            # Create state file if it doesn't exist
            ensure_file(self.state_file)
            
            # Read state file
            content = self.state_file.read_text(encoding='utf-8')
            
            # Parse state
            if content:
                self._state = json.loads(content)
            else:
                self._state = {}
                
        except Exception as e:
            raise StateError(f"Failed to load state: {str(e)}") from e
    
    def _save_state(self) -> None:
        """Save state to file.
        
        Raises:
            StateError: If state cannot be saved
        """
        try:
            # Create state file if it doesn't exist
            ensure_file(self.state_file)
            
            # Write state file
            content = json.dumps(self._state, indent=2)
            self.state_file.write_text(content, encoding='utf-8')
            
        except Exception as e:
            raise StateError(f"Failed to save state: {str(e)}") from e
    
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
            self._state.clear()
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