#!/usr/bin/env python3

import os
from pathlib import Path
from validation_manager import ValidationManager

def test_validation_manager():
    """Test the validation manager functionality."""
    
    # Get base directory from environment
    base_dir = os.getenv("NOVA_BASE_DIR")
    if not base_dir:
        raise ValueError("NOVA_BASE_DIR environment variable not set")
    
    print("🧪 Testing Validation Manager...")
    
    # Initialize validation manager
    validator = ValidationManager(base_dir)
    print("✅ Validation manager initialized")
    
    # Test directory permissions
    print("\n📝 Testing directory permissions...")
    dir_status = validator.check_directory_permissions()
    print(f"{'✅' if dir_status else '❌'} Directory permissions check {'passed' if dir_status else 'failed'}")
    
    # Test dependencies
    print("\n📝 Testing dependencies...")
    dep_status = validator.check_dependencies()
    print(f"{'✅' if dep_status else '❌'} Dependencies check {'passed' if dep_status else 'failed'}")
    
    # Test input file validation
    print("\n📝 Testing input file validation...")
    file_status, valid_files = validator.validate_input_files()
    print(f"{'✅' if file_status else '❌'} Input file validation {'passed' if file_status else 'failed'}")
    if file_status:
        print(f"  Found {len(valid_files)} valid markdown files:")
        for file_path in valid_files:
            print(f"  - {file_path.name}")
    
    # Run all checks
    print("\n📝 Running all validation checks...")
    success, results = validator.run_all_checks()
    
    print("\n🔍 Final Results:")
    for check, status in results.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {check}: {'Passed' if status else 'Failed'}")
    
    print(f"\n📝 Detailed report saved to: {os.getenv('NOVA_PROCESSING_DIR')}/validation_report.json")
    
    if not success:
        print("\n❌ Some validation checks failed. Please check the report for details.")
    else:
        print("\n✅ All validation checks passed!")

if __name__ == "__main__":
    test_validation_manager() 