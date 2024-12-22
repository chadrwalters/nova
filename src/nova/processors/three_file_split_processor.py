"""Processor for splitting aggregated markdown into summary, raw notes, and attachments."""

from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple, Set

from ..core.config import ProcessorConfig, NovaConfig
from ..core.errors import ProcessingError
from .base import BaseProcessor

class ThreeFileSplitProcessor(BaseProcessor):
    """Processor that splits aggregated markdown into three separate files."""
    
    def _setup(self) -> None:
        """Setup processor requirements."""
        config = self.config.options["components"]["three_file_split_processor"]["config"]
        self.output_files = config["output_files"]
        self.section_markers = config["section_markers"]
        self.cross_linking = config["cross_linking"]
        self.preserve_headers = config["preserve_headers"]
        
        # Regex patterns for finding references
        self.attachment_ref_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')  # Image/attachment references
        self.heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)  # Markdown headings

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
            
            # Process attachments first to gather reference information
            attachments_content, attachment_anchors = self._process_attachments(attachments_content)
            
            # Add cross-links and process references
            if self.cross_linking:
                summary_content = self._add_cross_links(summary_content, "summary")
                raw_notes_content = self._add_cross_links(raw_notes_content, "raw_notes")
                attachments_content = self._add_cross_links(attachments_content, "attachments")
                
                # Update references in summary and raw notes
                summary_content = self._update_attachment_refs(summary_content, attachment_anchors)
                raw_notes_content = self._update_attachment_refs(raw_notes_content, attachment_anchors)
            
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
    
    def _process_attachments(self, content: str) -> Tuple[str, Dict[str, str]]:
        """Process attachments section to create anchors for cross-referencing.
        
        Args:
            content: Attachments section content
            
        Returns:
            Tuple of (processed_content, anchor_mapping)
        """
        anchor_mapping = {}  # Maps original paths to anchor IDs
        lines = content.split('\n')
        processed_lines = []
        
        for line in lines:
            # Find attachment references
            for match in self.attachment_ref_pattern.finditer(line):
                alt_text, path = match.groups()
                # Create a unique anchor ID
                anchor_id = self._create_anchor_id(path)
                anchor_mapping[path] = anchor_id
                # Add anchor to the line
                line = f'<a id="{anchor_id}"></a>\n{line}'
            processed_lines.append(line)
        
        return '\n'.join(processed_lines), anchor_mapping
    
    def _update_attachment_refs(self, content: str, attachment_anchors: Dict[str, str]) -> str:
        """Update attachment references to point to the attachments file with anchors.
        
        Args:
            content: Section content
            attachment_anchors: Mapping of original paths to anchor IDs
            
        Returns:
            Content with updated references
        """
        attachments_file = self.output_files["attachments"]
        
        def replace_ref(match: re.Match) -> str:
            alt_text, path = match.groups()
            if path in attachment_anchors:
                return f'![{alt_text}]({attachments_file}#{attachment_anchors[path]})'
            return match.group(0)
        
        return self.attachment_ref_pattern.sub(replace_ref, content)
    
    def _create_anchor_id(self, path: str) -> str:
        """Create a unique anchor ID from a path.
        
        Args:
            path: Original file path
            
        Returns:
            Sanitized anchor ID
        """
        # Remove file extension and special characters
        base = Path(path).stem
        # Convert to lowercase and replace spaces/special chars with hyphens
        anchor = re.sub(r'[^a-z0-9]+', '-', base.lower()).strip('-')
        return f'attachment-{anchor}'
    
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