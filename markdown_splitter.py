#!/usr/bin/env python3

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import re

class MarkdownSplitter:
    """Splits aggregated markdown content into summary, raw notes, and attachments."""
    
    def __init__(self, input_dir: Path, output_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Create file handler
        log_file = output_dir / "splitter_processor.log"
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
        
        # Section markers
        self.section_markers = {
            'summary': "--==SUMMARY==--",
            'raw_notes': "--==RAW NOTES==--",
            'attachments': "--==ATTACHMENTS==--"
        }
        
        # Output files
        self.output_files = {
            'summary': "summary.md",
            'raw_notes': "raw_notes.md",
            'attachments': "attachments.md"
        }
    
    def process(self) -> Optional[Dict[str, Any]]:
        """Process the aggregated markdown file and split it into three files."""
        try:
            # Find aggregated markdown file
            input_file = self.input_dir / "all_merged_markdown.md"
            if not input_file.exists():
                self.logger.error(f"Input file not found: {input_file}")
                return None
            
            # Create output directory if it doesn't exist
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Read and split content
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split content into sections
            sections = self._split_content(content)
            
            # Write sections to files
            output_files = self._write_sections(sections)
            
            if output_files:
                self.logger.info("Successfully split content into three files")
                return {
                    'input_file': str(input_file),
                    'output_files': output_files
                }
            else:
                self.logger.error("Failed to write output files")
                return None
        
        except Exception as e:
            self.logger.error(f"Error processing file: {str(e)}")
            return None
    
    def _split_content(self, content: str) -> Dict[str, str]:
        """Split content into summary, raw notes, and attachments sections."""
        sections = {
            'summary': [],
            'raw_notes': [],
            'attachments': []
        }
        
        current_section = None  # Start with no section
        lines = content.split('\n')
        
        # Find all image and link references for attachments
        attachments = []
        for line in lines:
            # Match markdown image syntax ![alt](path)
            img_matches = re.findall(r'!\[.*?\]\((.*?)\)', line)
            attachments.extend(img_matches)
            
            # Match markdown link syntax [text](path)
            link_matches = re.findall(r'\[.*?\]\((.*?)\)', line)
            attachments.extend(link_matches)
        
        for line in lines:
            # Check for section markers
            if any(marker in line for marker in self.section_markers.values()):
                for section, marker in self.section_markers.items():
                    if marker in line:
                        current_section = section
                        break
                continue
            
            # Add line to current section if we're in one
            if current_section is not None:
                sections[current_section].append(line)
        
        # Add attachments to the attachments section
        if attachments:
            sections['attachments'].append("## Referenced Files")
            for attachment in sorted(set(attachments)):
                sections['attachments'].append(f"- {attachment}")
        
        # Convert lists to strings and ensure all sections exist
        result = {}
        for section in sections:
            content = '\n'.join(sections[section]).strip()
            if content:  # Only include non-empty sections
                result[section] = content
        
        return result
    
    def _write_sections(self, sections: Dict[str, str]) -> Optional[Dict[str, str]]:
        """Write sections to their respective files."""
        try:
            output_files = {}
            
            for section, content in sections.items():
                if not content:  # Skip empty sections
                    continue
                
                output_file = self.output_dir / self.output_files[section]
                with open(output_file, 'w', encoding='utf-8') as f:
                    # Add header
                    header = self._generate_header(section)
                    f.write(header)
                    
                    # Write content
                    f.write(content)
                    
                    # Add footer
                    footer = self._generate_footer(section)
                    f.write(footer)
                
                output_files[section] = str(output_file)
                self.logger.info(f"Created {section} file: {output_file}")
            
            if output_files:
                self.logger.info("Successfully split content into three files")
                return output_files
            else:
                self.logger.warning("No content to write")
                return None
        
        except Exception as e:
            self.logger.error(f"Error writing sections: {str(e)}")
            return None
    
    def _generate_header(self, section: str) -> str:
        """Generate header for a section file."""
        title = section.replace('_', ' ').title()
        return f"""# {title}

This file contains the {title.lower()} extracted from the aggregated markdown content.

---

"""
    
    def _generate_footer(self, section: str) -> str:
        """Generate footer for a section file."""
        return f"""

---
End of {section.replace('_', ' ').title()}
""" 