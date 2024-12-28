"""Core pipeline state management."""

from pathlib import Path
from typing import Dict, Any, Optional, List, Set
import json


class PipelineState:
    """Class for managing pipeline state."""
    
    def __init__(self, state_file: Optional[Path] = None):
        """Initialize pipeline state.
        
        Args:
            state_file: Optional path to state file
        """
        self.state_file = state_file
        self.state: Dict[str, Any] = {}
        self.processed_files: Set[str] = set()
        self.failed_files: Set[str] = set()
        self.skipped_files: Set[str] = set()
        
        if state_file and state_file.exists():
            self.load_state()
            
    def load_state(self) -> None:
        """Load state from file."""
        if not self.state_file:
            return
            
        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)
                self.state = data.get("state", {})
                self.processed_files = set(data.get("processed_files", []))
                self.failed_files = set(data.get("failed_files", []))
                self.skipped_files = set(data.get("skipped_files", []))
        except Exception as e:
            print(f"Failed to load state: {str(e)}")
            
    def save_state(self) -> None:
        """Save state to file."""
        if not self.state_file:
            return
            
        try:
            data = {
                "state": self.state,
                "processed_files": list(self.processed_files),
                "failed_files": list(self.failed_files),
                "skipped_files": list(self.skipped_files)
            }
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save state: {str(e)}")
            
    def mark_processed(self, file_path: str) -> None:
        """Mark a file as processed.
        
        Args:
            file_path: Path to processed file
        """
        self.processed_files.add(file_path)
        self.save_state()
        
    def mark_failed(self, file_path: str) -> None:
        """Mark a file as failed.
        
        Args:
            file_path: Path to failed file
        """
        self.failed_files.add(file_path)
        self.save_state()
        
    def mark_skipped(self, file_path: str) -> None:
        """Mark a file as skipped.
        
        Args:
            file_path: Path to skipped file
        """
        self.skipped_files.add(file_path)
        self.save_state()
        
    def is_processed(self, file_path: str) -> bool:
        """Check if a file has been processed.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file has been processed
        """
        return file_path in self.processed_files
        
    def is_failed(self, file_path: str) -> bool:
        """Check if a file has failed processing.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file has failed
        """
        return file_path in self.failed_files
        
    def is_skipped(self, file_path: str) -> bool:
        """Check if a file has been skipped.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file has been skipped
        """
        return file_path in self.skipped_files
        
    def get_state(self, key: str) -> Any:
        """Get state value.
        
        Args:
            key: State key
            
        Returns:
            State value or None if not found
        """
        return self.state.get(key)
        
    def set_state(self, key: str, value: Any) -> None:
        """Set state value.
        
        Args:
            key: State key
            value: State value
        """
        self.state[key] = value
        self.save_state()
        
    def clear_state(self) -> None:
        """Clear all state."""
        self.state.clear()
        self.processed_files.clear()
        self.failed_files.clear()
        self.skipped_files.clear()
        self.save_state() 