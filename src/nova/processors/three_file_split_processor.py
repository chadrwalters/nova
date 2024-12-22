"""Processor for splitting aggregated markdown into summary, raw notes, and attachments."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..core.config import ProcessorConfig, NovaConfig
from ..core.errors import ProcessingError
from .base import BaseProcessor

class ThreeFileSplitProcessor(BaseProcessor):
    """Processor that splits aggregated markdown into three separate files."""
    
    def _setup(self) -> None:
        """Setup processor requirements."""
        self.output_files = self.config.components["three_file_split_processor"]["config"]["output_files"]
        self.section_markers = self.config.components["three_file_split_processor"]["config"]["section_markers"]
        self.cross_linking = self.config.components["three_file_split_processor"]["config"]["cross_linking"]
        self.preserve_headers = self.config.components["three_file_split_processor"]["config"]["preserve_headers"]

    def process(self, input_path: Path, output_path: Path) -> Path:
        """Process the aggregated markdown file into three separate files.
        
        Args:
            input_path: Path to input aggregated markdown file
            output_path: Path to output directory
            
        Returns:
            Path to output directory containing the three files
        """
        try:
            # Read input file
            content = input_path.read_text(encoding='utf-8')
            
            # Split content into sections
            summary_content, raw_notes_content, attachments_content = self._split_content(content)
            
            # Add cross-links if enabled
            if self.cross_linking:
                summary_content = self._add_cross_links(summary_content, "summary")
                raw_notes_content = self._add_cross_links(raw_notes_content, "raw_notes")
                attachments_content = self._add_cross_links(attachments_content, "attachments")
            
            # Write output files
            output_path.mkdir(parents=True, exist_ok=True)
            
            summary_file = output_path / self.output_files["summary"]
            raw_notes_file = output_path / self.output_files["raw_notes"]
            attachments_file = output_path / self.output_files["attachments"]
            
            summary_file.write_text(summary_content, encoding='utf-8')
            raw_notes_file.write_text(raw_notes_content, encoding='utf-8')
            attachments_file.write_text(attachments_content, encoding='utf-8')
            
            self.logger.info(f"Successfully split content into three files in {output_path}")
            return output_path
            
        except Exception as e:
            raise ProcessingError(f"Failed to split content: {str(e)}") from e
    
    def _split_content(self, content: str) -> Tuple[str, str, str]:
        """Split content into summary, raw notes, and attachments sections.
        
        Args:
            content: Input markdown content
            
        Returns:
            Tuple of (summary_content, raw_notes_content, attachments_content)
        """
        sections = {
            "summary": [],
            "raw_notes": [],
            "attachments": []
        }
        
        current_section = "summary"  # Default to summary if no markers found
        lines = content.split('\n')
        
        for line in lines:
            # Check for section markers
            for section, marker in self.section_markers.items():
                if marker in line:
                    current_section = section
                    if self.preserve_headers:
                        sections[current_section].append(line)
                    break
            else:
                sections[current_section].append(line)
        
        return (
            '\n'.join(sections["summary"]),
            '\n'.join(sections["raw_notes"]),
            '\n'.join(sections["attachments"])
        )
    
    def _add_cross_links(self, content: str, section: str) -> str:
        """Add cross-links to other sections at the top of the content.
        
        Args:
            content: Section content
            section: Current section name
            
        Returns:
            Content with cross-links added
        """
        links = []
        for other_section, filename in self.output_files.items():
            if other_section != section:
                links.append(f"[Go to {other_section.replace('_', ' ').title()}]({filename})")
        
        if links:
            nav_section = " | ".join(links)
            return f"{nav_section}\n\n{content}"
        
        return content 