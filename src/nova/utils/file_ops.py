#!/usr/bin/env python3

import os
import re
import json
import chardet
import markdown
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from datetime import datetime

class AttachmentInfo:
    """Information about a discovered attachment."""
    
    def __init__(self, path: Path, ref_type: str, parent_file: Path):
        self.path = path
        self.ref_type = ref_type  # 'image', 'link', 'embed', etc.
        self.parent_file = parent_file
        self.exists = path.exists()
        self.mime_type = self._get_mime_type() if self.exists else None
        self.size = path.stat().st_size if self.exists else 0
        self.last_modified = datetime.fromtimestamp(path.stat().st_mtime).isoformat() if self.exists else None

    def _get_mime_type(self) -> str:
        """Get the MIME type of the attachment."""
        import magic
        return magic.from_file(str(self.path), mime=True)

    def to_dict(self) -> Dict:
        """Convert attachment info to dictionary."""
        return {
            "path": str(self.path),
            "ref_type": self.ref_type,
            "parent_file": str(self.parent_file),
            "exists": self.exists,
            "mime_type": self.mime_type,
            "size": self.size,
            "last_modified": self.last_modified
        }

class InputProcessor:
    """Processes input markdown files and discovers attachments."""
    
    def __init__(self, input_dir: Union[str, Path], base_dir: Union[str, Path]):
        """Initialize the input processor.
        
        Args:
            input_dir: Directory containing input files
            base_dir: Base directory for resolving relative paths
        """
        self.input_dir = Path(input_dir)
        self.base_dir = Path(base_dir)
        self.markdown_files: List[Path] = []
        self.attachments: Dict[str, AttachmentInfo] = {}
        self.processing_log: List[Dict] = []

    def _log_processing(self, file_path: Path, status: str, message: str) -> None:
        """Log a processing event.
        
        Args:
            file_path: Path to the file being processed
            status: Status of the operation
            message: Description or error message
        """
        self.processing_log.append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "file": str(file_path),
            "status": status,
            "message": message
        })

    def _find_markdown_files(self) -> List[Path]:
        """Find all markdown files in the input directory."""
        return list(self.input_dir.glob("**/*.md"))

    def _validate_markdown_file(self, file_path: Path) -> bool:
        """Validate a markdown file's encoding and syntax.
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            # Check file exists and is readable
            if not file_path.exists() or not os.access(file_path, os.R_OK):
                self._log_processing(file_path, "error", "File not accessible")
                return False

            # Check encoding
            with open(file_path, 'rb') as f:
                raw_content = f.read()
                result = chardet.detect(raw_content)
                if result['encoding'] not in ['utf-8', 'ascii']:
                    self._log_processing(file_path, "error", 
                        f"Invalid encoding: {result['encoding']}")
                    return False

            # Check markdown syntax
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                markdown.markdown(content)
                self._log_processing(file_path, "success", "Valid markdown file")
                return True

        except Exception as e:
            self._log_processing(file_path, "error", f"Validation error: {str(e)}")
            return False

    def _find_attachments(self, file_path: Path, content: str) -> Set[AttachmentInfo]:
        """Find all attachments referenced in a markdown file.
        
        Args:
            file_path: Path to the markdown file
            content: Content of the markdown file
            
        Returns:
            Set[AttachmentInfo]: Set of discovered attachments
        """
        attachments = set()
        
        # Find image references
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        for match in re.finditer(image_pattern, content):
            path = self._resolve_path(match.group(2), file_path)
            attachments.add(AttachmentInfo(path, 'image', file_path))

        # Find link references
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        for match in re.finditer(link_pattern, content):
            path = self._resolve_path(match.group(2), file_path)
            if path.suffix.lower() in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv', '.html']:
                attachments.add(AttachmentInfo(path, 'link', file_path))

        # Find embedded content markers
        embed_pattern = r'--==ATTACHMENT_BLOCK: ([^=]+)==--'
        for match in re.finditer(embed_pattern, content):
            path = self._resolve_path(match.group(1), file_path)
            attachments.add(AttachmentInfo(path, 'embed', file_path))

        return attachments

    def _resolve_path(self, path_str: str, relative_to: Path) -> Path:
        """Resolve a path relative to a file.
        
        Args:
            path_str: Path string to resolve
            relative_to: File path to resolve relative to
            
        Returns:
            Path: Resolved absolute path
        """
        path = Path(path_str)
        if path.is_absolute():
            return path
        return (relative_to.parent / path).resolve()

    def process_input(self) -> Tuple[bool, Dict]:
        """Process all input files and discover attachments.
        
        Returns:
            Tuple[bool, Dict]: (success status, processing results)
        """
        success = True
        self.markdown_files = self._find_markdown_files()
        
        if not self.markdown_files:
            self._log_processing(self.input_dir, "error", "No markdown files found")
            return False, self._get_results()

        for file_path in self.markdown_files:
            # Validate markdown
            if not self._validate_markdown_file(file_path):
                success = False
                continue

            # Find attachments
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    attachments = self._find_attachments(file_path, content)
                    for attachment in attachments:
                        self.attachments[str(attachment.path)] = attachment
                    self._log_processing(file_path, "success", 
                        f"Found {len(attachments)} attachments")
            except Exception as e:
                self._log_processing(file_path, "error", 
                    f"Error processing attachments: {str(e)}")
                success = False

        return success, self._get_results()

    def _get_results(self) -> Dict:
        """Get the processing results.
        
        Returns:
            Dict: Processing results and statistics
        """
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "input_directory": str(self.input_dir),
            "markdown_files": [str(f) for f in self.markdown_files],
            "attachments": {
                path: info.to_dict() 
                for path, info in self.attachments.items()
            },
            "statistics": {
                "total_files": len(self.markdown_files),
                "total_attachments": len(self.attachments),
                "attachment_types": {
                    ref_type: len([a for a in self.attachments.values() 
                                 if a.ref_type == ref_type])
                    for ref_type in ['image', 'link', 'embed']
                }
            },
            "processing_log": self.processing_log
        }

    def save_manifest(self, output_file: Union[str, Path]) -> None:
        """Save the attachment manifest to a file.
        
        Args:
            output_file: Path to save the manifest to
        """
        with open(output_file, 'w') as f:
            json.dump(self._get_results(), f, indent=4)

if __name__ == "__main__":
    # Get directories from environment
    input_dir = os.getenv("NOVA_INPUT_DIR")
    base_dir = os.getenv("NOVA_BASE_DIR")
    processing_dir = os.getenv("NOVA_PROCESSING_DIR")
    
    if not all([input_dir, base_dir, processing_dir]):
        print("Error: Required environment variables not set")
        exit(1)
    
    # Process input
    processor = InputProcessor(input_dir, base_dir)
    success, results = processor.process_input()
    
    # Save manifest
    manifest_file = Path(processing_dir) / "attachment_manifest.json"
    processor.save_manifest(manifest_file)
    
    # Print results
    print("\n📊 Processing Results:")
    stats = results["statistics"]
    print(f"Files processed: {stats['total_files']}")
    print(f"Attachments found: {stats['total_attachments']}")
    print("\nAttachment types:")
    for type_name, count in stats["attachment_types"].items():
        print(f"  - {type_name}: {count}")
    
    print(f"\n📝 Manifest saved to: {manifest_file}")
    
    if not success:
        print("\n❌ Some files had processing errors. Check the manifest for details.")
        exit(1)
    else:
        print("\n✅ All files processed successfully!") 