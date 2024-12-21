"""State management module for Nova document processor."""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from .logging import get_logger

class StateManager:
    """Manages processing state for Nova document processor."""
    
    def __init__(self, state_dir: Path):
        """Initialize state manager.
        
        Args:
            state_dir: Path to state directory
        """
        self.state_dir = Path(state_dir)
        self.logger = get_logger(__name__)
        self._ensure_state_dir()
        self.state: Dict[str, Any] = {}
        self._load_state()
    
    def _ensure_state_dir(self) -> None:
        """Ensure state directory exists."""
        try:
            # Check if state_dir exists and is a file
            if self.state_dir.exists() and not self.state_dir.is_dir():
                # Backup and remove the file
                backup_path = self.state_dir.with_suffix('.bak')
                self.logger.warning(f"State path exists as file, moving to {backup_path}")
                shutil.move(str(self.state_dir), str(backup_path))
            
            # Create main state directory
            self.state_dir.mkdir(parents=True, exist_ok=True)
            
            # Create phase state directories
            phase_dirs = ['markdown_parse', 'markdown_consolidate']
            for phase in phase_dirs:
                phase_dir = self.state_dir / phase
                if phase_dir.exists() and not phase_dir.is_dir():
                    # Backup and remove if it's a file
                    backup_path = phase_dir.with_suffix('.bak')
                    self.logger.warning(f"Phase state path exists as file, moving to {backup_path}")
                    shutil.move(str(phase_dir), str(backup_path))
                phase_dir.mkdir(parents=True, exist_ok=True)
                
        except Exception as e:
            if getattr(e, 'errno', None) != 17:  # Only raise if not EEXIST
                self.logger.error(f"Failed to create state directories: {e}")
                raise
            self.logger.debug("State directories already exist")
    
    def _load_state(self) -> None:
        """Load state from file."""
        state_file = self.state_dir / 'state.json'
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    self.state = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                # If state file is corrupted or can't be read, start fresh
                self.logger.warning(f"Could not load state file: {e}")
                self.state = {}
    
    def save(self) -> None:
        """Save state to file."""
        try:
            state_file = self.state_dir / 'state.json'
            with open(state_file, 'w') as f:
                json.dump(self.state, f, indent=2, default=str)
        except OSError as e:
            self.logger.error(f"Could not save state file: {e}")
    
    def update_file_state(self, phase: str, file_path: str, status: str, error: Optional[str] = None) -> None:
        """Update state for a file.
        
        Args:
            phase: Processing phase
            file_path: Path to file
            status: Processing status
            error: Error message if failed
        """
        if phase not in self.state:
            self.state[phase] = {}
            
        self.state[phase][file_path] = {
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'error': error
        }
        
        # Save after each update
        self.save()
    
    def get_file_state(self, phase: str, file_path: str) -> Optional[Dict[str, Any]]:
        """Get state for a file.
        
        Args:
            phase: Processing phase
            file_path: Path to file
            
        Returns:
            File state or None if not found
        """
        return self.state.get(phase, {}).get(file_path)
    
    def reset(self) -> None:
        """Reset all state."""
        self.state = {}
        self.save()