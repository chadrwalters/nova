#!/usr/bin/env python3

import os
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import shutil

class ConsolidateProcessor:
    """Consolidates markdown files with their attachments."""
    
    def __init__(self, input_dir: Path, output_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Create file handler
        log_file = output_dir / "consolidate_processor.log"
        fh = logging.FileHandler(str(log_file))
        fh.setLevel(logging.DEBUG)
        
        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
        # Regex patterns for attachment blocks
        self.attachment_start_pattern = re.compile(r'--==ATTACHMENT_BLOCK: (.+?)==--')
        self.attachment_end_pattern = re.compile(r'--==ATTACHMENT_BLOCK_END==--')
    
    def process_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Process a single markdown file."""
        try:
            self.logger.info(f"Processing file: {file_path}")
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract attachments and their content
            attachments = self._extract_attachments(content)
            
            # Create output directory structure
            output_path = self._get_output_path(file_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create attachments directory
            attachments_dir = output_path.parent / f"{output_path.stem}_attachments"
            attachments_dir.mkdir(exist_ok=True)
            
            # Process and copy attachments
            processed_attachments = self._process_attachments(attachments, file_path, attachments_dir)
            
            # Update content with new attachment paths
            updated_content = self._update_attachment_paths(content, processed_attachments)
            
            # Save consolidated file
            self._save_file(output_path, updated_content)
            
            return {
                'input_file': str(file_path),
                'output_file': str(output_path),
                'attachments_dir': str(attachments_dir),
                'attachments': processed_attachments
            }
        
        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {str(e)}")
            return None
    
    def _extract_attachments(self, content: str) -> List[Dict[str, Any]]:
        """Extract attachments and their content from markdown file."""
        attachments = []
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            match = self.attachment_start_pattern.search(line)
            
            if match:
                original_path = match.group(1)
                attachment_content = []
                i += 1
                
                # Collect content until end marker
                while i < len(lines):
                    if self.attachment_end_pattern.search(lines[i]):
                        break
                    attachment_content.append(lines[i])
                    i += 1
                
                attachments.append({
                    'original_path': original_path,
                    'content': '\n'.join(attachment_content)
                })
            
            i += 1
        
        return attachments
    
    def _process_attachments(self, attachments: List[Dict[str, Any]], 
                           source_file: Path,
                           attachments_dir: Path) -> List[Dict[str, Any]]:
        """Process and copy attachments to their new location."""
        processed = []
        
        for attachment in attachments:
            original_path = Path(attachment['original_path'])
            
            # Try to resolve the attachment path
            resolved_path = self._resolve_attachment_path(original_path, source_file)
            
            if resolved_path and resolved_path.exists():
                new_path = attachments_dir / original_path.name
                shutil.copy2(resolved_path, new_path)
                
                processed.append({
                    'original_path': str(original_path),
                    'new_path': str(new_path),
                    'content': attachment['content']
                })
            else:
                self.logger.warning(f"Original attachment not found: {original_path}")
                processed.append({
                    'original_path': str(original_path),
                    'new_path': None,
                    'content': attachment['content']
                })
        
        return processed
    
    def _resolve_attachment_path(self, path: Path, source_file: Path) -> Optional[Path]:
        """Resolve the actual path of an attachment."""
        try:
            # Check if path is absolute
            if path.is_absolute():
                return path if path.exists() else None
            
            # Try relative to source file
            relative_to_source = source_file.parent / path
            if relative_to_source.exists():
                return relative_to_source
            
            # Try relative to input directory
            relative_to_input = self.input_dir / path
            if relative_to_input.exists():
                return relative_to_input
            
            # Try just the filename in source file directory
            filename_only = source_file.parent / path.name
            if filename_only.exists():
                return filename_only
            
            return None
        except Exception as e:
            self.logger.error(f"Error resolving path {path}: {str(e)}")
            return None
    
    def _update_attachment_paths(self, content: str, 
                               processed_attachments: List[Dict[str, Any]]) -> str:
        """Update attachment paths in the content."""
        updated_content = content
        
        for attachment in processed_attachments:
            if attachment['new_path']:
                # Replace original path with new path in content
                original_path = attachment['original_path']
                new_path = attachment['new_path']
                updated_content = updated_content.replace(original_path, new_path)
        
        return updated_content
    
    def _get_output_path(self, input_path: Path) -> Path:
        """Get the output path for a processed file."""
        relative_path = input_path.relative_to(self.input_dir)
        return self.output_dir / relative_path
    
    def _save_file(self, output_path: Path, content: str):
        """Save the processed file."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.logger.info(f"Saved consolidated file: {output_path}")
        except Exception as e:
            self.logger.error(f"Error saving file {output_path}: {str(e)}")
    
    def process_directory(self) -> bool:
        """Process all markdown files in the input directory."""
        try:
            # Find all markdown files
            markdown_files = list(self.input_dir.glob('**/*.md'))
            self.logger.info(f"Found {len(markdown_files)} markdown files")
            
            # Process each file
            success = True
            for file_path in markdown_files:
                result = self.process_file(file_path)
                if not result:
                    success = False
            
            return success
        except Exception as e:
            self.logger.error(f"Error processing directory: {str(e)}")
            return False 