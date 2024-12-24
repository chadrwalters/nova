#!/usr/bin/env python3

import os
from pathlib import Path
from nova.core.state import StateManager

def test_state_manager(tmp_path):
    """Test the state manager functionality."""
    # Create test directories
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True)
    
    # Initialize state manager
    state_manager = StateManager(str(state_dir))
    
    # Test state operations
    state_manager.set_state("test_key", "test_value")
    assert state_manager.get_state("test_key") == "test_value"
    
    # Test state persistence
    state_manager.save()
    new_state_manager = StateManager(str(state_dir))
    assert new_state_manager.get_state("test_key") == "test_value"
    
    # Test state reset
    state_manager.reset()
    assert state_manager.get_state("test_key") is None
    
    # Test file state tracking
    state_manager.update_file_state("phase1", "test.md", "completed")
    file_state = state_manager.get_file_state("phase1", "test.md")
    assert file_state is not None
    assert file_state["status"] == "completed"

if __name__ == "__main__":
    test_state_manager() 