#!/usr/bin/env python3

import os
from pathlib import Path
from input_processor import InputProcessor

def test_input_processor():
    """Test the input processor functionality."""
    
    # Get directories from environment
    input_dir = os.getenv("NOVA_INPUT_DIR")
    base_dir = os.getenv("NOVA_BASE_DIR")
    processing_dir = os.getenv("NOVA_PROCESSING_DIR")
    
    if not all([input_dir, base_dir, processing_dir]):
        raise ValueError("Required environment variables not set")
    
    print("🧪 Testing Input Processor...")
    
    # Initialize processor
    processor = InputProcessor(input_dir, base_dir)
    print("✅ Input processor initialized")
    
    # Process input files
    print("\n📝 Processing input files...")
    success, results = processor.process_input()
    
    # Print results
    print("\n📊 Processing Results:")
    stats = results["statistics"]
    print(f"Files processed: {stats['total_files']}")
    print(f"Attachments found: {stats['total_attachments']}")
    
    print("\nAttachment types:")
    for type_name, count in stats["attachment_types"].items():
        print(f"  - {type_name}: {count}")
    
    print("\n📝 Attachment details:")
    for path, info in results["attachments"].items():
        print(f"\n  {info['ref_type'].upper()}: {Path(path).name}")
        print(f"    Parent: {Path(info['parent_file']).name}")
        print(f"    Exists: {info['exists']}")
        if info['exists']:
            print(f"    MIME Type: {info['mime_type']}")
            print(f"    Size: {info['size']} bytes")
    
    # Save manifest
    manifest_file = Path(processing_dir) / "attachment_manifest.json"
    processor.save_manifest(manifest_file)
    print(f"\n📝 Manifest saved to: {manifest_file}")
    
    if not success:
        print("\n❌ Some files had processing errors. Check the manifest for details.")
    else:
        print("\n✅ All files processed successfully!")

if __name__ == "__main__":
    test_input_processor() 