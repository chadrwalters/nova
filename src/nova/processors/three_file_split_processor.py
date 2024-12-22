"""Processor for splitting aggregated markdown into summary, raw notes, and attachments."""

from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple, Set, Any, Literal
import os
from enum import Enum

from ..core.config import ProcessorConfig, NovaConfig
from ..core.errors import ProcessingError
from .base import BaseProcessor

class ContentType(Enum):
    """Types of content that can be detected."""
    SUMMARY = "summary"
    RAW_NOTES = "raw_notes"
    ATTACHMENTS = "attachments"
    UNKNOWN = "unknown"

class ThreeFileSplitProcessor(BaseProcessor):
    """Processor that splits aggregated markdown into three separate files."""
    
    def __init__(self, processor_config: ProcessorConfig, nova_config: Optional[NovaConfig] = None):
        """Initialize the processor with configuration."""
        super().__init__(processor_config, nova_config)
        self.stats = {
            'input_files': 0,
            'attachments': 0,
            'raw_notes': 0,
            'summaries': 0,
            'expected_files': 0,
            'expected_attachments': 0,
            'content_sizes': {
                'input': 0,
                'summary': 0,
                'raw_notes': 0,
                'attachments': 0
            }
        }

    def _setup(self) -> None:
        """Setup processor requirements."""
        config = self.config.options["components"]["three_file_split_processor"]["config"]
        self.output_files = config["output_files"]
        self.section_markers = config["section_markers"]
        self.cross_linking = config["cross_linking"]
        self.preserve_headers = config["preserve_headers"]
        
        # Regex patterns for content detection
        self.summary_markers = re.compile(
            r'^(?:'
            r'## Refined Thoughts|'
            r'## Key Insights|'
            r'## Analysis|'
            r'## Nova Analysis|'
            r'## Progress Analysis|'
            r'## Enhanced Summary'
            r')',
            re.MULTILINE
        )
        
        self.raw_notes_markers = re.compile(
            r'^(?:'
            r'--==RAW NOTES==--|'
            r'## Raw Notes|'
            r'## Notes from|'
            r'## Meeting Notes|'
            r'## Communication|'
            r'## Journal Entry'
            r')',
            re.MULTILINE
        )
        
        # Attachment patterns
        self.attachment_ref_pattern = re.compile(
            r'(?:'
            r'!\[([^\]]*)\]\(([^)]+)\)|'  # Image references ![alt](url)
            r'\[([^\]]+)\]\(([^)]+\.(pdf|doc|docx|xls|xlsx|txt|csv|jpg|jpeg|png|gif))\)|'  # Named links to documents
            r'<(https?://[^>]+\.(pdf|doc|docx|xls|xlsx|txt|csv|jpg|jpeg|png|gif))>|'  # Bare URLs to documents
            r'\[Begin Attachment:|'  # Attachment markers
            r'<!-- \{"embed":"|'  # Embedded content
            r'--==ATTACHMENTS==--'  # Section marker
            r')'
        )
        
        self.heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

    def detect_content_type(self, content: str, current_section: Optional[str] = None) -> ContentType:
        """Analyze content to determine its type based on markers and structure.
        
        Args:
            content: The content block to analyze
            current_section: Optional current section marker from file structure
            
        Returns:
            ContentType enum indicating the detected type
        """
        # If we're in a marked section, that takes precedence
        if current_section:
            if current_section == "SUMMARY":
                return ContentType.SUMMARY
            elif current_section == "RAW_NOTES":
                return ContentType.RAW_NOTES
            elif current_section == "ATTACHMENTS":
                return ContentType.ATTACHMENTS
        
        # Check for summary markers
        if self.summary_markers.search(content):
            return ContentType.SUMMARY
            
        # Check for raw notes markers
        if self.raw_notes_markers.search(content):
            return ContentType.RAW_NOTES
            
        # Check for attachment markers
        if self.attachment_ref_pattern.search(content):
            return ContentType.ATTACHMENTS
            
        # If no clear markers, analyze content structure
        lines = content.split('\n')
        bullet_count = len([l for l in lines if l.strip().startswith('* ')])
        number_count = len([l for l in lines if re.match(r'^\d+\.', l.strip())])
        
        # If content has lots of bullets/numbers, likely a summary
        if (bullet_count + number_count) / len(lines) > 0.3:
            return ContentType.SUMMARY
            
        # Default to raw notes if no other patterns match
        return ContentType.RAW_NOTES

    def _add_navigation_header(self, content_type: ContentType) -> str:
        """Add navigation header to a content file."""
        links = []
        if content_type != ContentType.SUMMARY:
            links.append("[Go to Summary](summary.md)")
        if content_type != ContentType.RAW_NOTES:
            links.append("[Go to Raw Notes](raw_notes.md)")
        if content_type != ContentType.ATTACHMENTS:
            links.append("[Go to Attachments](attachments.md)")
        return " | ".join(links) + "\n\n"

    def _update_internal_references(self, content: str, content_type: ContentType) -> str:
        """Update internal references to point to the correct files."""
        # Update image references to point to attachments
        content = re.sub(
            r'!\[(.*?)\]\((.*?)\)',
            lambda m: f'![{m.group(1)}](attachments.md#attachment-{os.path.splitext(os.path.basename(m.group(2)))[0]})',
            content
        )
        
        # Update section references in [[...]] format
        content = re.sub(
            r'\[\[(.*?)\]\]',
            lambda m: self._resolve_section_reference(m.group(1), content_type),
            content
        )
        
        # Update section references in [...](...) format
        content = re.sub(
            r'\[(.*?)\]\(#(.*?)\)',
            lambda m: self._resolve_section_reference(m.group(1), content_type),
            content
        )
        
        return content

    def _resolve_section_reference(self, ref: str, current_type: ContentType) -> str:
        """Resolve a section reference to the appropriate file."""
        # Common summary section titles
        summary_sections = {
            'refined thoughts', 'key insights', 'analysis', 'progress analysis',
            'enhanced summary', 'nova analysis'
        }
        
        # Common raw notes sections
        raw_notes_sections = {
            'raw notes', 'meeting notes', 'communication', 'journal entry'
        }
        
        ref_lower = ref.lower()
        anchor_id = self._create_section_anchor(ref)
        
        if any(section in ref_lower for section in summary_sections):
            return f'[{ref}](summary.md#{anchor_id})'
        elif any(section in ref_lower for section in raw_notes_sections):
            return f'[{ref}](raw_notes.md#{anchor_id})'
        else:
            # Default to same file if unclear
            current_file = {
                ContentType.SUMMARY: 'summary.md',
                ContentType.RAW_NOTES: 'raw_notes.md',
                ContentType.ATTACHMENTS: 'attachments.md'
            }[current_type]
            return f'[{ref}]({current_file}#{anchor_id})'

    def _create_section_anchor(self, section: str) -> str:
        """Create an anchor ID for a section reference."""
        # Convert to lowercase and replace spaces/special chars with hyphens
        return re.sub(r'[^a-z0-9]+', '-', section.lower()).strip('-')

    def _split_content(self, content: str) -> Tuple[str, str, str]:
        """Split the content into summary, raw notes, and attachments sections."""
        # Track input size
        self.stats['content_sizes']['input'] = len(content.encode('utf-8'))
        
        # Initialize sections
        summary_content = []
        raw_notes_content = []
        attachments_content = []

        # Split content into lines
        lines = content.split('\n')
        current_section = None
        current_file = None
        buffer = []

        for line in lines:
            # Check for section markers
            if '--==SUMMARY==--' in line:
                if buffer and current_section != "SUMMARY":
                    # Route any content before first marker to raw notes
                    raw_notes_content.extend(buffer)
                current_section = "SUMMARY"
                buffer = []
            elif '--==RAW NOTES==--' in line:
                if buffer:
                    if current_section == "SUMMARY":
                        summary_content.extend(buffer)
                    else:
                        raw_notes_content.extend(buffer)
                current_section = "RAW_NOTES"
                buffer = []
            elif '--==ATTACHMENTS==--' in line:
                if buffer:
                    if current_section == "SUMMARY":
                        summary_content.extend(buffer)
                    elif current_section == "RAW_NOTES":
                        raw_notes_content.extend(buffer)
                current_section = "ATTACHMENTS"
                buffer = []
            elif line.startswith('## Start of file:'):
                if buffer:
                    if current_section == "SUMMARY":
                        summary_content.extend(buffer)
                    elif current_section == "RAW_NOTES":
                        raw_notes_content.extend(buffer)
                    elif current_section == "ATTACHMENTS":
                        attachments_content.extend(buffer)
                current_file = line.replace('## Start of file:', '').strip()
                buffer = []
            else:
                buffer.append(line)

        # Process final buffer
        if buffer:
            if current_section == "SUMMARY":
                summary_content.extend(buffer)
            elif current_section == "RAW_NOTES":
                raw_notes_content.extend(buffer)
            elif current_section == "ATTACHMENTS":
                attachments_content.extend(buffer)

        # Add navigation and update references
        summary = (
            self._add_navigation_header(ContentType.SUMMARY) +
            "# Summary\n\n" +
            '\n'.join(summary_content)
        )
        
        raw_notes = (
            self._add_navigation_header(ContentType.RAW_NOTES) +
            "# Raw Notes\n\n" +
            '\n'.join(raw_notes_content)
        )
        
        attachments = (
            self._add_navigation_header(ContentType.ATTACHMENTS) +
            "# Attachments\n\n" +
            '\n'.join(attachments_content)
        )

        # Track output sizes
        self.stats['content_sizes']['summary'] = len(summary.encode('utf-8'))
        self.stats['content_sizes']['raw_notes'] = len(raw_notes.encode('utf-8'))
        self.stats['content_sizes']['attachments'] = len(attachments.encode('utf-8'))

        return summary.strip(), raw_notes.strip(), attachments.strip()

    def _route_content(self, buffer: List[str], content_type: ContentType, 
                      summary_content: List[str], raw_notes_content: List[str], 
                      attachments_content: List[str], current_file: Optional[str] = None) -> None:
        """Route content buffer to appropriate output list based on content type."""
        if not buffer:
            return
            
        content = '\n'.join(buffer)
        
        if content_type == ContentType.SUMMARY:
            summary_content.extend(buffer)
            self.stats['summaries'] += 1
        elif content_type == ContentType.RAW_NOTES:
            if current_file:
                raw_notes_content.extend([f"\n## Notes from: {current_file}\n"])
            raw_notes_content.extend(buffer)
            self.stats['raw_notes'] += 1
        elif content_type == ContentType.ATTACHMENTS:
            attachments_content.extend(buffer)
            self.stats['attachments'] += 1

    def process(self, input_path: Path, output_path: Path) -> Path:
        """Process the aggregated markdown file into three separate files.
        
        Args:
            input_path: Path to input aggregated markdown file
            output_path: Path to output directory
            
        Returns:
            Path to output directory containing the three files
        """
        try:
            # Count expected files from input directory
            input_dir = Path(os.getenv('NOVA_INPUT_DIR', ''))
            if input_dir.exists():
                self.stats['expected_files'] = len([f for f in input_dir.glob('*.md') if f.is_file()])
                # Count expected attachments from subdirectories
                for subdir in input_dir.glob('*'):
                    if subdir.is_dir():
                        self.stats['expected_attachments'] += len([f for f in subdir.glob('*') if f.is_file()])

            # Read input file
            content = input_path.read_text(encoding='utf-8')
            
            # Split content into sections
            summary, raw_notes, attachments = self._split_content(content)
            
            # Process attachments first to gather reference information
            attachments, attachment_anchors = self._process_attachments(attachments)
            
            # Update references in summary and raw notes
            summary = self._update_internal_references(summary, ContentType.SUMMARY)
            raw_notes = self._update_internal_references(raw_notes, ContentType.RAW_NOTES)
            attachments = self._update_internal_references(attachments, ContentType.ATTACHMENTS)
            
            # Update attachment references
            summary = self._update_attachment_refs(summary, attachment_anchors)
            raw_notes = self._update_attachment_refs(raw_notes, attachment_anchors)
            
            # Write output files
            output_path.mkdir(parents=True, exist_ok=True)
            
            for section, content in [("summary", summary), ("raw_notes", raw_notes), ("attachments", attachments)]:
                output_file = output_path / self.output_files[section]
                output_file.write_text(content, encoding='utf-8')
            
            # Log statistics and validation guidance
            self._log_statistics()
            
            return output_path
            
        except Exception as e:
            raise ProcessingError(f"Failed to split content: {str(e)}") from e
    
    def _process_attachments(self, content: str) -> Tuple[str, Dict[str, str]]:
        """Process attachments section to add anchors for images and build anchor mapping.
        
        Args:
            content: Attachments section content
            
        Returns:
            Tuple of (processed_content, anchor_mapping)
        """
        lines = content.split('\n')
        processed_lines = []
        anchor_mapping = {}
        
        for line in lines:
            # Check for image reference
            match = re.search(r'!\[(.*?)\]\((.*?)\)', line)
            if match:
                image_path = match.group(2)
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                anchor_id = f'attachment-{base_name}'
                anchor_mapping[image_path] = anchor_id
                processed_lines.append(f'<a id="{anchor_id}"></a>')
            processed_lines.append(line)
        
        return '\n'.join(processed_lines), anchor_mapping
    
    def _update_attachment_refs(self, content: str, attachment_anchors: Dict[str, str]) -> str:
        """Update attachment references to point to the correct anchors."""
        def replace_ref(match: re.Match) -> str:
            alt_text = match.group(1)
            path = match.group(2)
            if path in attachment_anchors:
                return f'![{alt_text}](attachments.md#{attachment_anchors[path]})'
            return match.group(0)
        
        # Update image references to point to attachments
        content = re.sub(r'!\[(.*?)\]\((.*?)\)', replace_ref, content)
        return content
    
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
    
    def _log_statistics(self):
        """Log processing statistics and validation guidance."""
        from ..core.logging import info, warning, success, detail, path

        info("\n📊 Processing Statistics:")
        detail(f"Expected input files: {self.stats['expected_files']}")
        detail(f"Actual processed files: {self.stats['input_files']}")
        detail(f"Expected attachments: {self.stats['expected_attachments']}")
        detail(f"Summaries found: {self.stats['summaries']}")
        detail(f"Raw notes sections: {self.stats['raw_notes']}")
        
        # Validation guidance with clear formatting
        if self.stats['expected_files'] != self.stats['input_files']:
            warning("\n⚠️  File Count Mismatch:")
            detail(f"  • Expected {self.stats['expected_files']} files")
            detail(f"  • Processed {self.stats['input_files']} files")
            detail("  • Please check if all input files were properly aggregated")
            
        if self.stats['summaries'] < self.stats['input_files']:
            warning("\n⚠️  Low Summary Count:")
            detail(f"  • Only {self.stats['summaries']} summaries for {self.stats['input_files']} files")
            detail("  • Check if content before --==RAW NOTES==-- is properly formatted")
            
        if self.stats['raw_notes'] < self.stats['input_files']:
            warning("\n⚠️  Low Raw Notes Count:")
            detail(f"  • Only {self.stats['raw_notes']} raw notes for {self.stats['input_files']} files")
            detail("  • Check if content after --==RAW NOTES==-- is properly formatted")

        # Overall status
        if all([
            self.stats['expected_files'] == self.stats['input_files'],
            self.stats['summaries'] >= self.stats['input_files'],
            self.stats['raw_notes'] >= self.stats['input_files']
        ]):
            success("\n✅ All validation checks passed!")
        else:
            warning("\n⚠️  Some validation checks failed. Please review the warnings above.")