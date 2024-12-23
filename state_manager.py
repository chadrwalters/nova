#!/usr/bin/env python3

import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

class StateManager:
    """Manages processing state and file tracking for the Nova pipeline."""
    
    def __init__(self, processing_dir: Union[str, Path]):
        """Initialize the state manager.
        
        Args:
            processing_dir: Base processing directory path
        """
        self.processing_dir = Path(processing_dir)
        self.state_file = self.processing_dir / '.state'
        self._load_state()

    def _load_state(self) -> None:
        """Load the current state from the state file."""
        if not self.state_file.exists():
            raise FileNotFoundError(f"State file not found at {self.state_file}")
        
        with open(self.state_file, 'r') as f:
            self.state = json.load(f)

    def _save_state(self) -> None:
        """Save the current state to the state file."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=4)

    def _calculate_file_hash(self, file_path: Union[str, Path]) -> str:
        """Calculate SHA-256 hash of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: Hex digest of file hash
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def track_file(self, file_path: Union[str, Path]) -> Dict:
        """Add or update a file in the state tracking.
        
        Args:
            file_path: Path to the file to track
            
        Returns:
            Dict: File tracking information
        """
        file_path = Path(file_path)
        file_info = {
            "path": str(file_path),
            "hash": self._calculate_file_hash(file_path),
            "last_modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
            "size": file_path.stat().st_size,
            "processing_status": {
                "parse": "pending",
                "consolidate": "pending",
                "aggregate": "pending",
                "split": "pending"
            }
        }
        
        # Update processed_files list
        existing_files = [f for f in self.state["processed_files"] if f["path"] != str(file_path)]
        existing_files.append(file_info)
        self.state["processed_files"] = existing_files
        
        self._save_state()
        return file_info

    def update_phase_status(self, phase: str, status: str) -> None:
        """Update the status of a processing phase.
        
        Args:
            phase: Name of the phase
            status: New status value
        """
        if phase not in self.state["phase_status"]:
            raise ValueError(f"Invalid phase: {phase}")
        
        self.state["phase_status"][phase] = status
        self.state["last_update"] = datetime.utcnow().isoformat() + "Z"
        self._save_state()

    def update_file_status(self, file_path: Union[str, Path], phase: str, status: str) -> None:
        """Update the processing status of a file for a specific phase.
        
        Args:
            file_path: Path to the file
            phase: Processing phase name
            status: New status value
        """
        file_path = str(Path(file_path))
        for file_info in self.state["processed_files"]:
            if file_info["path"] == file_path:
                file_info["processing_status"][phase] = status
                self._save_state()
                return
        raise ValueError(f"File not found in state: {file_path}")

    def get_file_status(self, file_path: Union[str, Path]) -> Optional[Dict]:
        """Get the current processing status of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Optional[Dict]: File status information or None if not found
        """
        file_path = str(Path(file_path))
        for file_info in self.state["processed_files"]:
            if file_info["path"] == file_path:
                return file_info
        return None

    def get_phase_status(self, phase: str) -> str:
        """Get the current status of a processing phase.
        
        Args:
            phase: Name of the phase
            
        Returns:
            str: Phase status
        """
        if phase not in self.state["phase_status"]:
            raise ValueError(f"Invalid phase: {phase}")
        return self.state["phase_status"][phase]

    def get_pending_files(self, phase: str) -> List[Dict]:
        """Get list of files pending processing for a specific phase.
        
        Args:
            phase: Name of the phase
            
        Returns:
            List[Dict]: List of pending files
        """
        return [
            f for f in self.state["processed_files"]
            if f["processing_status"][phase] == "pending"
        ]

    def has_changed(self, file_path: Union[str, Path]) -> bool:
        """Check if a file has changed since last tracking.
        
        Args:
            file_path: Path to the file
            
        Returns:
            bool: True if file has changed, False otherwise
        """
        file_path = Path(file_path)
        current_hash = self._calculate_file_hash(file_path)
        
        file_info = self.get_file_status(file_path)
        if file_info is None:
            return True
            
        return file_info["hash"] != current_hash

if __name__ == "__main__":
    # Example usage
    import os
    
    # Get processing directory from environment
    processing_dir = os.getenv("NOVA_PROCESSING_DIR")
    if not processing_dir:
        raise ValueError("NOVA_PROCESSING_DIR environment variable not set")
    
    # Initialize state manager
    state_manager = StateManager(processing_dir)
    
    # Example: Update phase status
    state_manager.update_phase_status("parse", "in_progress")
    
    # Example: Track a file
    input_file = Path(os.getenv("NOVA_INPUT_DIR", "")) / "example.md"
    if input_file.exists():
        file_info = state_manager.track_file(input_file)
        print(f"Tracked file: {file_info}") 