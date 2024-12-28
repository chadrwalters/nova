"""Split phase of the Nova pipeline."""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union
import os
import logging

from ..config.manager import ConfigManager
from ..models.document import DocumentMetadata


class SplitPhase:
    """Split phase of the Nova pipeline."""
    
    def __init__(self, config: ConfigManager) -> None:
        """Initialize split phase.
        
        Args:
            config: Nova configuration manager.
        """
        self.config = config
        self.logger = logging.getLogger("nova.phases.split")
        
        # Initialize consolidated files
        self.summary_sections = []
        self.raw_notes_sections = []
        self.attachment_sections = []
        
        # Track processed files
        self.processed_files = set()
    
    async def process(
        self,
        file_path: Path,
        output_path: Path,
        metadata: Optional[DocumentMetadata] = None,
    ) -> DocumentMetadata:
        """Process a file.
        
        Args:
            file_path: Path to file.
            output_path: Path to output file.
            metadata: Document metadata.
            
        Returns:
            Document metadata.
        """
        try:
            # Get relative path from input dir
            rel_path = file_path.relative_to(self.config.input_dir)
            
            # Look for parsed file
            parsed_path = self.config.processing_dir / "phases/parse" / rel_path
            parsed_path = parsed_path.with_name(f"{parsed_path.stem}.parsed.md")
            
            self.logger.debug(f"Looking for parsed file at: {parsed_path}")
            
            if not parsed_path.exists():
                self.logger.error(f"Parsed file not found: {parsed_path}")
                raise ValueError(f"Parsed file not found: {parsed_path}")
            
            # Read the parsed file
            with open(parsed_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Split into sections
            sections = self._split_sections(content)
            
            # Add sections to consolidated files
            if sections["summary"]:
                self.summary_sections.append({
                    "file": rel_path,
                    "content": sections["summary"]
                })
            
            if sections["raw_notes"]:
                self.raw_notes_sections.append({
                    "file": rel_path,
                    "content": sections["raw_notes"]
                })
            
            if sections["attachments"]:
                self.attachment_sections.append({
                    "file": rel_path,
                    "content": sections["attachments"]
                })
            
            # Update metadata
            if metadata is None:
                metadata = DocumentMetadata.from_file(file_path)
            metadata.processed = True
            metadata.add_output_file(output_path)
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to process file {file_path}: {str(e)}")
            if metadata is not None:
                metadata.add_error("split", str(e))
            return metadata
    
    def _split_sections(self, content: str) -> Dict[str, str]:
        """Split content into sections.
        
        Args:
            content: File content.
            
        Returns:
            Dict with summary, raw_notes, and attachments sections.
        """
        sections = {
            "summary": "",
            "raw_notes": "",
            "attachments": ""
        }
        
        # Split on ---RAW NOTES--- marker
        parts = content.split("---RAW NOTES---")
        
        if len(parts) > 0:
            sections["summary"] = parts[0].strip()
        
        if len(parts) > 1:
            sections["raw_notes"] = parts[1].strip()
        
        # Extract attachment sections (marked with ```attachment)
        import re
        attachment_blocks = re.findall(r"```attachment.*?```", content, re.DOTALL)
        sections["attachments"] = "\n\n".join(attachment_blocks)
        
        return sections
    
    async def _write_consolidated_files(self, output_dir: Path) -> None:
        """Write consolidated files.
        
        Args:
            output_dir: Output directory.
        """
        # Write summary.md
        if self.summary_sections:
            summary_path = output_dir / "summary.md"
            with open(summary_path, "w") as f:
                f.write("# Summary\n\n")
                for section in self.summary_sections:
                    f.write(f"## {section['file']}\n\n")
                    f.write(section["content"])
                    f.write("\n\n")
        
        # Write raw_notes.md
        if self.raw_notes_sections:
            raw_notes_path = output_dir / "raw_notes.md"
            with open(raw_notes_path, "w") as f:
                f.write("# Raw Notes\n\n")
                for section in self.raw_notes_sections:
                    f.write(f"## {section['file']}\n\n")
                    f.write(section["content"])
                    f.write("\n\n")
        
        # Write attachments.md
        if self.attachment_sections:
            attachments_path = output_dir / "attachments.md"
            with open(attachments_path, "w") as f:
                f.write("# Attachments\n\n")
                for section in self.attachment_sections:
                    f.write(f"## {section['file']}\n\n")
                    f.write(section["content"])
                    f.write("\n\n") 