#!/usr/bin/env python3

import os
from pathlib import Path
from directory_manager import DirectoryManager

def test_directory_manager():
    """Test the directory manager functionality."""
    
    # Get base directory from environment
    base_dir = os.getenv("NOVA_BASE_DIR")
    if not base_dir:
        raise ValueError("NOVA_BASE_DIR environment variable not set")
    
    print("🧪 Testing Directory Manager...")
    
    # Initialize manager
    manager = DirectoryManager(base_dir)
    print("✅ Directory manager initialized")
    
    # Validate current structure
    print("\n📝 Validating current structure...")
    valid = manager.validate_structure()
    print(f"{'✅' if valid else '❌'} Structure validation {'passed' if valid else 'failed'}")
    
    # Create missing directories
    print("\n📝 Creating missing directories...")
    created = manager.create_structure()
    print(f"{'✅' if created else '❌'} Directory creation {'succeeded' if created else 'failed'}")
    
    # Validate structure again
    print("\n📝 Re-validating structure...")
    valid = manager.validate_structure()
    print(f"{'✅' if valid else '❌'} Structure validation {'passed' if valid else 'failed'}")
    
    # Print directory tree
    print("\n📁 Directory Structure:")
    def print_tree(config: dict, indent: int = 0):
        for key, value in config.items():
            if isinstance(value, dict):
                print("  " * indent + f"└── {key}/")
                print_tree(value, indent + 1)
            else:
                path = Path(value)
                exists = "✅" if path.exists() else "❌"
                writable = "📝" if os.access(path, os.W_OK) else "🔒"
                print("  " * indent + f"└── {key}: {exists} {writable}")
    
    print_tree(manager.required_dirs)
    
    # Save validation report
    report_file = Path(os.getenv("NOVA_PROCESSING_DIR", "")) / "directory_validation.json"
    manager.save_validation_report(report_file)
    print(f"\n📝 Validation report saved to: {report_file}")
    
    if not valid:
        print("\n❌ Directory structure validation failed. Check the report for details.")
    else:
        print("\n✅ Directory structure validated successfully!")

if __name__ == "__main__":
    test_directory_manager() 