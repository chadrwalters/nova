"""Handler for splitting markdown into summary, raw notes, and attachments."""

import os
from pathlib import Path
import shutil
import re
from typing import Dict, Any, Optional, List, Set, Tuple

from nova.core.models.result import ProcessingResult
from nova.phases.core.base_handler import BaseHandler, HandlerResult
from nova.core.utils.monitoring import MonitoringManager
from nova.core.models.state import HandlerState


class SplitHandler(BaseHandler):
    """Handler for splitting markdown into summary, raw notes, and attachments."""
    
    SECTION_MARKERS = {
        "summary": "--==SUMMARY==--",
        "raw_notes": "--==RAW NOTES==--",
        "attachments": "--==ATTACHMENTS==--"
    }
    
    ATTACHMENT_MARKERS = {
        "start": "--==ATTACHMENT_BLOCK: {filename}==--",
        "end": "--==ATTACHMENT_BLOCK_END==--"
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the handler.
        
        Args:
            config: Handler configuration
        """
        super().__init__(config)
        self.output_dir = Path(config.get("output_dir")) if config else None
        self.monitoring = MonitoringManager()
        self.monitoring.start()  # Start monitoring immediately
        self.state = HandlerState()
        
        # Additional configuration
        if config:
            self.section_markers = config.get("section_markers", self.SECTION_MARKERS)
            self.attachment_markers = config.get("attachment_markers", self.ATTACHMENT_MARKERS)
            self.output_files = config.get("output_files", {
                "summary": "summary.md",
                "raw_notes": "raw_notes.md",
                "attachments": "attachments.md"
            })
            self.cross_linking = config.get("cross_linking", True)
            self.preserve_headers = config.get("preserve_headers", True)
        else:
            self.section_markers = self.SECTION_MARKERS
            self.attachment_markers = self.ATTACHMENT_MARKERS
            self.output_files = {
                "summary": "summary.md",
                "raw_notes": "raw_notes.md",
                "attachments": "attachments.md"
            }
            self.cross_linking = True
            self.preserve_headers = True
    
    async def can_handle(self, file_path: Path) -> bool:
        """Check if the file can be handled.
        
        Args:
            file_path: Path to the file
            
        Returns:
            bool: True if the file can be handled
        """
        try:
            # Only handle markdown files
            if file_path.suffix.lower() != '.md':
                return False
            
            # Check if file exists and is readable
            if not file_path.exists() or not os.access(file_path, os.R_OK):
                self.state.errors.append(f"File not accessible: {file_path}")
                self.monitoring.metrics["errors"] += 1
                return False
            
            return True
            
        except Exception as e:
            self.state.errors.append(f"Error checking file: {str(e)}")
            self.monitoring.metrics["errors"] += 1
            return False
    
    def _split_content(self, content: str) -> Tuple[str, str, str]:
        """Split content into summary, raw notes, and attachments.
        
        Args:
            content: Content to split
            
        Returns:
            Tuple of (summary, raw_notes, attachments)
        """
        # Initialize sections
        summary = []
        raw_notes = []
        attachments = []
        current_section = summary  # Default to summary
        
        # Split into lines
        lines = content.split('\n')
        
        # Process each line
        for line in lines:
            # Check for section markers
            if line.strip() == self.section_markers["summary"]:
                current_section = summary
                continue
            elif line.strip() == self.section_markers["raw_notes"]:
                current_section = raw_notes
                continue
            elif line.strip() == self.section_markers["attachments"]:
                current_section = attachments
                continue
            
            # Add line to current section
            current_section.append(line)
        
        # Join sections back into strings
        return (
            '\n'.join(summary).strip(),
            '\n'.join(raw_notes).strip(),
            '\n'.join(attachments).strip()
        )
    
    def _add_cross_links(self, content: str, section_name: str) -> str:
        """Add cross-links to other sections.
        
        Args:
            content: Content to add links to
            section_name: Current section name
            
        Returns:
            Content with cross-links
        """
        if not self.cross_linking:
            return content
        
        links = "\n\n---\n\nSee also:\n"
        
        if section_name != "summary":
            links += f"- [Summary]({self.output_files['summary']})\n"
        if section_name != "raw_notes":
            links += f"- [Raw Notes]({self.output_files['raw_notes']})\n"
        if section_name != "attachments":
            links += f"- [Attachments]({self.output_files['attachments']})\n"
        
        return content + links
    
    def _write_section(self, content: str, section_name: str) -> Path:
        """Write section content to file.
        
        Args:
            content: Content to write
            section_name: Section name
            
        Returns:
            Path to output file
        """
        # Create output path
        output_path = self.output_dir / self.output_files[section_name]
        
        # Create parent directories
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Add cross-links
        if content:
            content = self._add_cross_links(content, section_name)
        
        # Write content
        output_path.write_text(content, encoding='utf-8')
        
        return output_path
    
    async def process(self, file_path: Path) -> ProcessingResult:
        """Process the markdown file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            ProcessingResult: Processing result
        """
        if not self.output_dir:
            error = "No output directory specified"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            return ProcessingResult(success=False, errors=[error])
        
        if not file_path.exists():
            error = f"File not found: {file_path}"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            self.state.failed_files.add(file_path)
            return ProcessingResult(success=False, errors=[error])
        
        try:
            # Start monitoring
            with self.monitoring.monitor_operation("process_markdown_file"):
                # Read content
                content = file_path.read_text(encoding='utf-8')
                
                # Split content
                summary, raw_notes, attachments = self._split_content(content)
                
                # Write sections
                summary_path = self._write_section(summary, "summary")
                raw_notes_path = self._write_section(raw_notes, "raw_notes")
                attachments_path = self._write_section(attachments, "attachments")
                
                # Update state
                self.state.processed_files.add(file_path)
                self.monitoring.metrics["files_processed"] += 1
                
                # Create metadata
                metadata = {
                    "original_path": str(file_path),
                    "output_files": {
                        "summary": str(summary_path),
                        "raw_notes": str(raw_notes_path),
                        "attachments": str(attachments_path)
                    },
                    "metrics": {
                        "summary_size": len(summary),
                        "raw_notes_size": len(raw_notes),
                        "attachments_size": len(attachments)
                    }
                }
                
                return ProcessingResult(
                    success=True,
                    content=str(summary_path),  # Return summary path as main content
                    metadata=metadata
                )
                
        except Exception as e:
            error = f"Error processing file {file_path}: {str(e)}"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            self.state.failed_files.add(file_path)
            return ProcessingResult(success=False, errors=[error])
    
    def validate(self, result: ProcessingResult) -> bool:
        """Validate the processing result.
        
        Args:
            result: Processing result to validate
            
        Returns:
            bool: True if the result is valid
        """
        if not result.success:
            return False
            
        if not result.content:
            error = "No content in processing result"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            return False
            
        return True
    
    def validate_output(self, result: HandlerResult) -> bool:
        """Validate the processing results.
        
        Args:
            result: The HandlerResult to validate
            
        Returns:
            bool: True if results are valid
        """
        if not result.content:
            error = "No content in processing result"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            return False
            
        if not result.metadata:
            error = "No metadata in processing result"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            return False
            
        if not result.metadata.get("original_path"):
            error = "No original path in metadata"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            return False
            
        if not result.metadata.get("output_files"):
            error = "No output files in metadata"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            return False
            
        return True
    
    async def cleanup(self):
        """Clean up resources."""
        try:
            # Clean up output files
            if self.output_dir and self.output_dir.exists():
                for file in self.output_dir.iterdir():
                    if file.is_file():
                        file.unlink()
                    elif file.is_dir():
                        shutil.rmtree(file)
            
            # Stop monitoring
            self.monitoring.stop()
            
            # Update state
            self.state.end_time = self.monitoring.state["end_time"]
            
        except Exception as e:
            error = f"Error during cleanup: {str(e)}"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1 