#!/usr/bin/env python3

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import datetime

class AggregateProcessor:
    """Aggregates multiple markdown files into a single file."""
    
    def __init__(self, input_dir: Path, output_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Create file handler
        log_file = output_dir / "aggregate_processor.log"
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
    
    def process(self) -> Optional[Dict[str, Any]]:
        """Process all markdown files and aggregate them into a single file."""
        try:
            # Find all markdown files
            markdown_files = sorted(list(self.input_dir.glob('**/*.md')))
            self.logger.info(f"Found {len(markdown_files)} markdown files")
            
            if not markdown_files:
                self.logger.warning("No markdown files found")
                return None
            
            # Create output directory if it doesn't exist
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create aggregated file
            output_file = self.output_dir / "all_merged_markdown.md"
            
            # Process files and write to output
            processed_files = self._process_files(markdown_files, output_file)
            
            if processed_files:
                self.logger.info(f"Successfully aggregated {len(processed_files)} files")
                return {
                    'output_file': str(output_file),
                    'processed_files': processed_files
                }
            else:
                self.logger.error("Failed to process files")
                return None
        
        except Exception as e:
            self.logger.error(f"Error processing files: {str(e)}")
            return None
    
    def _process_files(self, markdown_files: List[Path], output_file: Path) -> List[Dict[str, Any]]:
        """Process markdown files and write to output file."""
        processed_files = []
        
        try:
            with open(output_file, 'w', encoding='utf-8') as out:
                # Write header
                header = self._generate_header()
                out.write(header)
                
                # Write summary section marker
                out.write("\n--==SUMMARY==--\n\n")
                
                # Write raw notes section marker
                out.write("\n--==RAW NOTES==--\n\n")
                
                # Process each file
                for file_path in markdown_files:
                    try:
                        # Read file content
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Add file separator
                        separator = self._generate_file_separator(file_path)
                        out.write(separator)
                        
                        # Write content
                        out.write(content)
                        out.write("\n\n")
                        
                        processed_files.append({
                            'input_file': str(file_path),
                            'relative_path': str(file_path.relative_to(self.input_dir))
                        })
                        
                        self.logger.info(f"Processed file: {file_path}")
                    
                    except Exception as e:
                        self.logger.error(f"Error processing file {file_path}: {str(e)}")
                
                # Write attachments section marker
                out.write("\n--==ATTACHMENTS==--\n\n")
                
                # Write footer with file index
                footer = self._generate_footer(processed_files)
                out.write(footer)
            
            return processed_files
        
        except Exception as e:
            self.logger.error(f"Error writing to output file: {str(e)}")
            return []
    
    def _generate_header(self) -> str:
        """Generate header for the aggregated file."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""# Aggregated Markdown Files
Generated on: {timestamp}

This file contains the aggregated content of all markdown files from the input directory.
Each file's content is separated by markers indicating the original file path.

---

"""
    
    def _generate_file_separator(self, file_path: Path) -> str:
        """Generate separator between files."""
        relative_path = file_path.relative_to(self.input_dir)
        return f"""
---
File: {relative_path}
---

"""
    
    def _generate_footer(self, processed_files: List[Dict[str, Any]]) -> str:
        """Generate footer with file index."""
        footer = "\n\n---\n# File Index\n\n"
        for i, file_info in enumerate(processed_files, 1):
            relative_path = file_info['relative_path']
            footer += f"{i}. {relative_path}\n"
        return footer 