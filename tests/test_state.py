#!/usr/bin/env python3

import os
from pathlib import Path
from state_manager import StateManager

def test_state_manager():
    """Test the state manager functionality."""
    
    # Get environment variables
    processing_dir = os.getenv("NOVA_PROCESSING_DIR")
    input_dir = os.getenv("NOVA_INPUT_DIR")
    
    if not processing_dir or not input_dir:
        raise ValueError("Required environment variables not set")
    
    print("🧪 Testing State Manager...")
    
    # Initialize state manager
    state_manager = StateManager(processing_dir)
    print("✅ State manager initialized")
    
    # Test phase status updates
    print("\n📝 Testing phase status updates...")
    for phase in ["parse", "consolidate", "aggregate", "split"]:
        state_manager.update_phase_status(phase, "pending")
        status = state_manager.get_phase_status(phase)
        print(f"  ✓ {phase}: {status}")
    
    # Test file tracking
    print("\n📝 Testing file tracking...")
    input_path = Path(input_dir)
    markdown_files = list(input_path.glob("*.md"))
    
    if not markdown_files:
        print("  ⚠️  No markdown files found in input directory")
    else:
        for file_path in markdown_files:
            print(f"\n  Processing: {file_path.name}")
            
            # Track file
            file_info = state_manager.track_file(file_path)
            print(f"  ✓ File tracked: {file_path.name}")
            print(f"    - Hash: {file_info['hash'][:8]}...")
            print(f"    - Size: {file_info['size']} bytes")
            print(f"    - Last Modified: {file_info['last_modified']}")
            
            # Test status updates
            state_manager.update_file_status(file_path, "parse", "in_progress")
            status = state_manager.get_file_status(file_path)
            print(f"    - Status updated: {status['processing_status']['parse']}")
            
            # Test change detection
            changed = state_manager.has_changed(file_path)
            print(f"    - Changed since tracking: {changed}")
    
    # Test pending files
    print("\n📝 Testing pending files query...")
    for phase in ["parse", "consolidate", "aggregate", "split"]:
        pending = state_manager.get_pending_files(phase)
        print(f"  ✓ {phase}: {len(pending)} files pending")
    
    print("\n✅ All tests completed successfully!")

if __name__ == "__main__":
    test_state_manager() 