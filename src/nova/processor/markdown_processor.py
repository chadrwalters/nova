"""Processor for markdown content."""

import logging
import re
import os
import json
from pathlib import Path
from collections import defaultdict
from typing import Any, Dict, List

class MarkdownProcessor:
    """Processor for markdown content."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def _is_text_file(self, path: str) -> bool:
        """Check if a file is a text file based on extension."""
        text_extensions = {'.txt', '.md', '.json', '.csv', '.html', '.xml', '.yml', '.yaml'}
        return Path(path).suffix.lower() in text_extensions

    def _extract_attachments(self, content: str, source_file: str) -> List[Dict[str, Any]]:
        """Extract attachments from markdown content.
        
        Args:
            content: The markdown content to process
            source_file: The source file path
            
        Returns:
            List of attachment dictionaries containing metadata and paths
        """
        attachments = []
        lines = content.split('\n')
        
        # Regular expressions for finding markdown links and images
        link_pattern = r'(!?\[([^\]]+)\]\(([^)]+)\))'
        
        # Keep track of the current section and context buffer
        current_section = 'summary'  # Default to summary section
        context_buffer = []
        in_list = False
        
        for i, line in enumerate(lines):
            # Track sections
            if line.startswith('--==') and line.endswith('==--'):
                current_section = line[4:-4].lower()  # Remove markers and convert to lowercase
                context_buffer = []  # Reset context buffer at section boundaries
                in_list = False
                continue
                
            # Track if we're in a list
            if line.strip().startswith(('* ', '- ', '1. ')):
                in_list = True
            elif line.strip() and not line.strip().startswith(('  ', '   ', '    ')):  # Not indented
                in_list = False
            
            # Add line to context buffer if it's meaningful
            if line.strip() and not any(line.startswith(x) for x in ('--==', '#', '---')):
                # For list items, include the whole list as context
                if in_list:
                    context_buffer.append(line.strip())
                else:
                    context_buffer.append(line.strip())
                    # Keep buffer at reasonable size for non-list content
                    if len(context_buffer) > 5:
                        context_buffer.pop(0)
            
            # Look for attachments in this line
            for match in re.finditer(link_pattern, line):
                full_match, text, path = match.groups()
                
                # Skip if this is not a file link
                if path.startswith(('http://', 'https://', '#', '/')):
                    continue
                    
                # Get context from buffer and surrounding lines
                context_lines = []
                
                # Add lines from context buffer
                if in_list:
                    # For lists, include all buffered list items
                    context_lines.extend(context_buffer)
                else:
                    # For regular content, include recent context
                    context_lines.extend(context_buffer[:-1])  # Exclude current line
                
                # Add following lines for additional context
                for j in range(i + 1, min(len(lines), i + 3)):
                    next_line = lines[j].strip()
                    if next_line and not any(next_line.startswith(x) for x in ('--==', '#', '---')):
                        context_lines.append(next_line)
                
                # Convert image links in context to reference markers
                processed_context_lines = []
                for context_line in context_lines:
                    # Replace image/link patterns with reference markers
                    for ctx_match in re.finditer(link_pattern, context_line):
                        ctx_full_match, ctx_text, ctx_path = ctx_match.groups()
                        if not ctx_path.startswith(('http://', 'https://', '#', '/')):
                            file_type = self._get_file_type(ctx_path)
                            filename = Path(ctx_path).stem
                            ref = f"[ATTACH:{file_type}:{filename}]"
                            context_line = context_line.replace(ctx_full_match, ref)
                    processed_context_lines.append(context_line)
                
                # Build context string
                context = '\n'.join(processed_context_lines)
                
                # Get file type and create reference marker
                file_type = self._get_file_type(path)
                filename = Path(path).stem
                ref = f"[ATTACH:{file_type}:{filename}]"
                
                # Build attachment info
                attachment = {
                    'path': path,
                    'text': text,
                    'context': context,
                    'section': current_section,
                    'source_file': source_file,
                    'date': self._extract_date(source_file),
                    'type': file_type,
                    'is_image': full_match.startswith('!'),
                    'ref': ref
                }
                
                attachments.append(attachment)
        
        return attachments

    def _extract_date(self, file_path: str) -> str:
        """Extract date from file path if available."""
        match = re.search(r'(\d{8})', str(file_path))
        return match.group(1) if match else 'unknown'
        
    def _get_file_type(self, path: str) -> str:
        """Get standardized file type from path."""
        ext = Path(path).suffix.lower()
        type_map = {
            '.pdf': 'PDF',
            '.doc': 'DOC',
            '.docx': 'DOC',
            '.jpg': 'JPG',
            '.jpeg': 'JPG',
            '.png': 'PNG',
            '.heic': 'JPG',
            '.xlsx': 'EXCEL',
            '.xls': 'EXCEL',
            '.csv': 'EXCEL',
            '.txt': 'TXT',
            '.json': 'JSON',
            '.html': 'DOC',
            '.md': 'DOC'
        }
        return type_map.get(ext, 'OTHER')

    def _build_attachments_markdown(self, attachments: List[Dict[str, Any]]) -> str:
        """Build a markdown string containing all attachments with their context.
        
        Args:
            attachments: List of attachment dictionaries containing metadata and paths
            
        Returns:
            A markdown string containing all attachments organized by type
        """
        if not attachments:
            return "# Attachments\n\nNo attachments found."
        
        # Group attachments by date and type
        by_date = defaultdict(lambda: defaultdict(list))
        for attachment in attachments:
            date = self._extract_date(attachment['source_file'])
            file_type = attachment['type']
            by_date[date][file_type].append(attachment)
        
        # Build the markdown content
        content = ["# Attachments"]
        
        for date in sorted(by_date.keys()):
            content.append(f"\n## {date}")
            
            for file_type in sorted(by_date[date].keys()):
                content.append(f"\n### {file_type} Files\n")
                
                for attachment in sorted(by_date[date][file_type], key=lambda x: x['path']):
                    # Use the reference marker
                    content.append(f"#### {attachment['ref']}\n")
                    
                    # Add context if available
                    if attachment['context']:
                        content.append("Context:")
                        # Convert any remaining image/link patterns to reference markers
                        link_pattern = r'(!?\[([^\]]+)\]\(([^)]+)\))'
                        for line in attachment['context'].split('\n'):
                            # Replace image/link patterns with reference markers
                            for match in re.finditer(link_pattern, line):
                                full_match, text, path = match.groups()
                                if not path.startswith(('http://', 'https://', '#', '/')):
                                    file_type = self._get_file_type(path)
                                    filename = Path(path).stem
                                    ref = f"[ATTACH:{file_type}:{filename}]"
                                    line = line.replace(full_match, ref)
                            content.append(f"> {line}")
                        content.append("")  # Add a blank line after context
                    
                    # Add source information
                    source_info = [f"From {os.path.basename(attachment['source_file'])}"]
                    if attachment['section']:
                        source_info.append(f"in {attachment['section'].title()} section")
                    content.append(f"Source: {', '.join(source_info)}\n")
        
        return "\n".join(content) 