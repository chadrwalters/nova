"""Markdown content classification utilities."""

# Standard library imports
import logging
import re
from pathlib import Path
from typing import List, Optional, Pattern, Dict, Any

# Nova package imports
from nova.models.parsed_result import ParsedResult

logger = logging.getLogger(__name__)

class MarkdownClassifier:
    """Classifier for markdown content."""
    
    def __init__(self):
        """Initialize patterns for content classification."""
        # Summary patterns
        self.summary_patterns = [
            re.compile(r'(?m)^#\s*Summary\s*\n(.*?)(?=^#|\Z)', re.DOTALL),
            re.compile(r'(?m)^##\s*Key Points\s*\n(.*?)(?=^#|\Z)', re.DOTALL),
            re.compile(r'(?m)^##\s*Overview\s*\n(.*?)(?=^#|\Z)', re.DOTALL)
        ]
        
        # Raw notes patterns
        self.raw_notes_patterns = [
            re.compile(r'(?m)^#\s*Raw Notes\s*\n(.*?)(?=^#|\Z)', re.DOTALL),
            re.compile(r'(?m)^##\s*Notes\s*\n(.*?)(?=^#|\Z)', re.DOTALL),
            re.compile(r'(?m)^##\s*Details\s*\n(.*?)(?=^#|\Z)', re.DOTALL)
        ]
        
        # Attachment patterns
        self.attachment_patterns = [
            re.compile(r'!\[([^\]]*)\]\(([^)]+)\)'),  # Images
            re.compile(r'\[([^\]]+)\]\(([^)]+)\)'),   # Links
            re.compile(r'```[^\n]*\n(.*?)```', re.DOTALL),  # Code blocks
            re.compile(r'--==ATTACHMENT_BLOCK: (.*?)==--(.*?)--==ATTACHMENT_BLOCK_END==--', re.DOTALL)  # Attachment blocks
        ]
    
    def classify_content(
        self,
        content: str,
        source_file: Optional[str] = None,
        input_file: str = "stdin",
        output_file: str = "stdout"
    ) -> ParsedResult:
        """Classify markdown content into sections.
        
        Args:
            content: Markdown content to classify
            source_file: Original source file
            input_file: Input file path
            output_file: Output file path
            
        Returns:
            ParsedResult with classified content
        """
        # Initialize result
        result = ParsedResult(
            input_file=input_file,
            output_file=output_file,
            content=content,
            source_file=source_file or "",
            combined_markdown=content
        )
        
        # Extract summaries
        for pattern in self.summary_patterns:
            matches = pattern.finditer(content)
            for match in matches:
                summary = match.group(0).strip()
                if summary and summary not in result.summary_blocks:
                    result.summary_blocks.append(summary)
        
        # Extract raw notes
        for pattern in self.raw_notes_patterns:
            matches = pattern.finditer(content)
            for match in matches:
                notes = match.group(0).strip()
                if notes and notes not in result.raw_notes:
                    result.raw_notes.append(notes)
        
        # Extract attachments
        for pattern in self.attachment_patterns:
            matches = pattern.finditer(content)
            for match in matches:
                attachment = self._process_attachment_match(match)
                if attachment and attachment not in result.attachments:
                    result.attachments.append(attachment)
        
        # Add remaining content to raw notes
        remaining = content
        for section in result.summary_blocks + result.raw_notes:
            remaining = remaining.replace(section, '')
        
        for attachment in result.attachments:
            if isinstance(attachment, dict):
                remaining = remaining.replace(attachment['original_match'], '')
            else:
                remaining = remaining.replace(str(attachment), '')
        
        remaining = remaining.strip()
        if remaining and remaining not in result.raw_notes:
            result.raw_notes.append(remaining)
        
        return result
    
    def _process_attachment_match(self, match: re.Match) -> Optional[Dict[str, Any]]:
        """Process a regex match for attachments.
        
        Args:
            match: Regex match object
            
        Returns:
            Dictionary containing attachment info or None
        """
        groups = match.groups()
        
        if len(groups) == 0:  # Code blocks
            return {
                'type': 'code',
                'content': match.group(0),
                'original_match': match.group(0)
            }
        elif len(groups) == 2:  # Images or links
            title = groups[0]
            path = groups[1]
            
            if match.group(0).startswith('!'):  # Image
                return {
                    'type': 'image',
                    'title': title,
                    'path': path,
                    'original_match': match.group(0)
                }
            else:  # Link
                return {
                    'type': 'block',
                    'filename': title,
                    'content': path,
                    'original_match': match.group(0)
                }
        
        return None
    
    def save_sections(
        self,
        result: ParsedResult,
        output_dir: Path,
        create_dirs: bool = True
    ) -> None:
        """Save classified sections to files.
        
        Args:
            result: ParsedResult with classified content
            output_dir: Directory to save files
            create_dirs: Whether to create directories
        """
        if create_dirs:
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save summaries
        if result.summary_blocks:
            summary_file = output_dir / "summary.md"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("\n\n".join(result.summary_blocks))
        
        # Save raw notes
        if result.raw_notes:
            notes_file = output_dir / "raw_notes.md"
            with open(notes_file, 'w', encoding='utf-8') as f:
                f.write("\n\n".join(result.raw_notes))
        
        # Save attachments
        if result.attachments:
            attachments_dir = output_dir / "attachments"
            attachments_dir.mkdir(exist_ok=True)
            
            for i, attachment in enumerate(result.attachments):
                if isinstance(attachment, dict):
                    if attachment['type'] == 'block':
                        block_file = attachments_dir / f"{attachment['filename']}"
                        with open(block_file, 'w', encoding='utf-8') as f:
                            f.write(attachment['content'])
                    elif attachment['type'] == 'code':
                        block_file = attachments_dir / f"code_block_{i}.txt"
                        with open(block_file, 'w', encoding='utf-8') as f:
                            f.write(attachment['content'])
                    else:
                        # Copy image/document to attachments directory
                        original = Path(attachment['path'])
                        if original.exists():
                            new_path = attachments_dir / original.name
                            with open(original, 'rb') as src, open(new_path, 'wb') as dst:
                                dst.write(src.read())
                else:
                    # Save unknown attachment type
                    block_file = attachments_dir / f"attachment_{i}.txt"
                    with open(block_file, 'w', encoding='utf-8') as f:
                        f.write(str(attachment)) 