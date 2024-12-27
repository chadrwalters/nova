"""Handler for aggregating markdown files into a single document."""

import os
from pathlib import Path
import shutil
import re
from typing import Dict, Any, Optional, List, Set

from nova.core.models.result import ProcessingResult
from nova.phases.core.base_handler import BaseHandler, HandlerResult
from nova.core.utils.monitoring import MonitoringManager
from nova.core.models.state import HandlerState


class AggregateHandler(BaseHandler):
    """Handler for aggregating markdown files into a single document."""
    
    SECTION_MARKERS = {
        "start": "<!-- START_FILE: {filename} -->",
        "end": "<!-- END_FILE: {filename} -->",
        "separator": "\n---\n"
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
            self.output_filename = config.get("output_filename", "all_merged_markdown.md")
            self.section_markers = config.get("section_markers", self.SECTION_MARKERS)
            self.include_file_headers = config.get("include_file_headers", True)
            self.add_separators = config.get("add_separators", True)
            self.add_toc = config.get("add_toc", True)
        else:
            self.output_filename = "all_merged_markdown.md"
            self.section_markers = self.SECTION_MARKERS
            self.include_file_headers = True
            self.add_separators = True
            self.add_toc = True
    
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
    
    def _extract_title(self, content: str) -> str:
        """Extract title from markdown content.
        
        Args:
            content: Markdown content
            
        Returns:
            Title or filename if no title found
        """
        # Look for h1 header
        h1_pattern = r'^#\s+(.+)$'
        match = re.search(h1_pattern, content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        
        # Look for setext-style h1
        setext_pattern = r'^(.+)\n=+\s*$'
        match = re.search(setext_pattern, content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        
        return None
    
    def _generate_toc(self, sections: List[Dict[str, Any]]) -> str:
        """Generate table of contents.
        
        Args:
            sections: List of section info
            
        Returns:
            Table of contents markdown
        """
        toc = "# Table of Contents\n\n"
        
        for i, section in enumerate(sections, 1):
            title = section["title"] or f"Section {i}"
            filename = section["filename"]
            toc += f"{i}. [{title}](#{filename})\n"
        
        return toc + "\n"
    
    def _add_navigation(self, content: str, prev_link: Optional[str] = None,
                       next_link: Optional[str] = None) -> str:
        """Add navigation links to content.
        
        Args:
            content: Content to add navigation to
            prev_link: Previous section link
            next_link: Next section link
            
        Returns:
            Content with navigation
        """
        nav = "\n\n---\n\n"
        
        if prev_link:
            nav += f"← Previous: {prev_link} | "
        if next_link:
            nav += f"Next: {next_link} →"
        
        nav += " | [↑ Back to Top](#table-of-contents)\n"
        
        return content + nav
    
    async def process(self, file_paths: List[Path]) -> ProcessingResult:
        """Process the markdown files.
        
        Args:
            file_paths: List of files to process
            
        Returns:
            ProcessingResult: Processing result
        """
        if not self.output_dir:
            error = "No output directory specified"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            return ProcessingResult(success=False, errors=[error])
        
        if not file_paths:
            error = "No files to process"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            return ProcessingResult(success=False, errors=[error])
        
        try:
            # Start monitoring
            with self.monitoring.monitor_operation("process_markdown_files"):
                # Create output path
                output_path = self.output_dir / self.output_filename
                
                # Create parent directories
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Process each file
                sections = []
                aggregated_content = ""
                
                for file_path in file_paths:
                    try:
                        # Read content
                        content = file_path.read_text(encoding='utf-8')
                        
                        # Extract title
                        title = self._extract_title(content)
                        
                        # Add section info
                        sections.append({
                            "filename": file_path.stem,
                            "title": title,
                            "content": content
                        })
                        
                        # Update state
                        self.state.processed_files.add(file_path)
                        self.monitoring.metrics["files_processed"] = len(self.state.processed_files)
                        
                    except Exception as e:
                        error = f"Error processing file {file_path}: {str(e)}"
                        self.state.errors.append(error)
                        self.monitoring.metrics["errors"] += 1
                        self.state.failed_files.add(file_path)
                
                # Generate table of contents
                if self.add_toc:
                    aggregated_content += self._generate_toc(sections)
                
                # Add sections with navigation
                for i, section in enumerate(sections):
                    # Add section markers
                    if self.include_file_headers:
                        aggregated_content += self.section_markers["start"].format(
                            filename=section["filename"]
                        ) + "\n\n"
                    
                    # Add content
                    aggregated_content += section["content"]
                    
                    # Add section end marker
                    if self.include_file_headers:
                        aggregated_content += "\n\n" + self.section_markers["end"].format(
                            filename=section["filename"]
                        )
                    
                    # Add navigation
                    prev_section = sections[i - 1] if i > 0 else None
                    next_section = sections[i + 1] if i < len(sections) - 1 else None
                    
                    prev_link = f"[{prev_section['title']}](#{prev_section['filename']})" if prev_section else None
                    next_link = f"[{next_section['title']}](#{next_section['filename']})" if next_section else None
                    
                    aggregated_content = self._add_navigation(
                        aggregated_content,
                        prev_link,
                        next_link
                    )
                    
                    # Add separator
                    if self.add_separators and i < len(sections) - 1:
                        aggregated_content += self.section_markers["separator"]
                
                # Write output file
                output_path.write_text(aggregated_content, encoding='utf-8')
                
                # Create metadata
                metadata = {
                    "output_path": str(output_path),
                    "sections": [
                        {
                            "filename": section["filename"],
                            "title": section["title"]
                        }
                        for section in sections
                    ],
                    "metrics": {
                        "files_processed": len(sections),
                        "content_size": len(aggregated_content)
                    }
                }
                
                return ProcessingResult(
                    success=True,
                    content=str(output_path),
                    metadata=metadata
                )
                
        except Exception as e:
            error = f"Error aggregating files: {str(e)}"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
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
            
        if not result.metadata.get("output_path"):
            error = "No output path in metadata"
            self.state.errors.append(error)
            self.monitoring.metrics["errors"] += 1
            return False
            
        if not result.metadata.get("sections"):
            error = "No sections in metadata"
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