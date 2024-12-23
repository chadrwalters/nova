#!/usr/bin/env python3

import os
from pathlib import Path
from attachment_processor import create_processor

def test_attachment_processors():
    """Test the attachment processor functionality."""
    
    # Get directories from environment
    input_dir = os.getenv("NOVA_INPUT_DIR")
    processing_dir = os.getenv("NOVA_PROCESSING_DIR")
    
    if not all([input_dir, processing_dir]):
        raise ValueError("Required environment variables not set")
    
    print("🧪 Testing Attachment Processors...")
    
    # Find test files
    test_files = []
    for ext in ['.html', '.csv', '.xlsx', '.pdf', '.docx', '.jpg', '.heic']:
        test_files.extend(Path(input_dir).glob(f"**/*{ext}"))
    
    if not test_files:
        print("❌ No test files found")
        return
    
    print(f"\n📝 Found {len(test_files)} test files")
    
    # Process each file
    for file_path in test_files:
        print(f"\n📄 Processing: {file_path.name}")
        
        # Create processor
        processor = create_processor(file_path, Path(processing_dir))
        if not processor:
            print(f"❌ No processor available for {file_path.suffix}")
            continue
        
        # Process file
        markdown_content = processor.process()
        if markdown_content:
            print("✅ Processing successful")
            print("  Type:", processor.__class__.__name__)
            print("  MIME:", processor.mime_type)
            print("  Output size:", len(markdown_content))
            
            # Show sample of markdown content
            sample = markdown_content[:200] + "..." if len(markdown_content) > 200 else markdown_content
            print("\n  Sample output:")
            print("  " + "\n  ".join(sample.split('\n')))
        else:
            print("❌ Processing failed")
            print("  Check processing log for details")
    
    print("\n✅ Testing completed!")

if __name__ == "__main__":
    test_attachment_processors() 