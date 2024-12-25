"""Markdown content classifier."""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..models.parsed_result import ParsedResult

class MarkdownClassifier:
    """Classifies markdown content into different sections."""
    
    def __init__(self):
        """Initialize classifier."""
        # Patterns for identifying content types
        self.summary_patterns = [
            r'^#\s*Summary\b',
            r'^#\s*Overview\b',
            r'^#\s*Key Points\b',
            r'^##\s*Summary\b',
            r'^##\s*Overview\b',
            r'^##\s*Key Points\b',
            r'Overview:\s*$',
            r'Summary:\s*$',
            r'Key Points:\s*$'
        ]
        
        self.attachment_patterns = {
            'image': r'!\[(.*?)\]\((.*?)\)',  # Image
            'document': r'\[(.*?)\]\((.*?\.(?:pdf|docx?|xlsx?|csv|txt))\)',  # Document links
            'block': r'--==ATTACHMENT_BLOCK: (.*?)==--\n(.*?)--==ATTACHMENT_BLOCK_END==--'  # Attachment blocks
        }
    
    def classify_content(self, content: str, input_file: str = "stdin", output_file: str = "stdout") -> ParsedResult:
        """Classify markdown content into sections.
        
        Args:
            content: Markdown content to classify
            input_file: Optional input file path
            output_file: Optional output file path
            
        Returns:
            ParsedResult containing classified content
        """
        # Initialize result
        result = ParsedResult(
            input_file=input_file,
            output_file=output_file,
            content=content or "",  # Handle None or empty string
            combined_markdown=content or "",  # Set combined markdown immediately
            source_file=""
        )
        
        # If content is empty, return empty result
        if not content:
            return result
        
        # Split into blocks
        blocks = self._split_into_blocks(content)
        
        # Process each block
        for block in blocks:
            # Check if summary block
            if self._is_summary_block(block):
                result.summary_blocks.append(block)
            else:
                result.raw_notes.append(block)
            
            # Extract attachments
            attachments = self._extract_attachments(block)
            if attachments:
                result.attachments.extend(attachments)
        
        return result
    
    def _split_into_blocks(self, content: str) -> List[str]:
        """Split content into logical blocks.
        
        Args:
            content: Content to split
            
        Returns:
            List of content blocks
        """
        # Split on headers and blank lines
        blocks = []
        current_block = []
        
        for line in content.split('\n'):
            line_stripped = line.strip()
            
            # Start new block on headers
            if line.startswith('#'):
                if current_block:
                    blocks.append('\n'.join(current_block))
                current_block = [line]
            # Handle blank lines
            elif not line_stripped:
                if current_block:
                    blocks.append('\n'.join(current_block))
                    current_block = []
            else:
                current_block.append(line)
        
        # Add final block
        if current_block:
            blocks.append('\n'.join(current_block))
        
        return [b for b in blocks if b.strip()]
    
    def _is_summary_block(self, block: str) -> bool:
        """Check if block is a summary block.
        
        Args:
            block: Block to check
            
        Returns:
            True if summary block, False otherwise
        """
        for pattern in self.summary_patterns:
            if re.search(pattern, block, re.MULTILINE):
                return True
        return False
    
    def _extract_attachments(self, block: str) -> List[Dict[str, str]]:
        """Extract attachments from block.
        
        Args:
            block: Block to extract from
            
        Returns:
            List of attachment dictionaries
        """
        attachments = []
        
        # Extract images
        for match in re.finditer(self.attachment_patterns['image'], block):
            attachments.append({
                'type': 'image',
                'title': match.group(1),
                'path': match.group(2),
                'original_match': match.group(0)
            })
        
        # Extract document links
        for match in re.finditer(self.attachment_patterns['document'], block):
            attachments.append({
                'type': 'document',
                'title': match.group(1),
                'path': match.group(2),
                'original_match': match.group(0)
            })
        
        # Extract attachment blocks
        for match in re.finditer(self.attachment_patterns['block'], block, re.DOTALL):
            attachments.append({
                'type': 'block',
                'filename': match.group(1),
                'content': match.group(2).strip(),
                'original_match': match.group(0)
            })
        
        return attachments 