"""Markdown utilities for Nova."""
import os
import re
from pathlib import Path
from typing import Dict, Optional

from nova.models.document import DocumentMetadata


def update_markdown_links(
    markdown_path: Path,
    attachment_metadata: Dict[str, DocumentMetadata]
) -> None:
    """Update links in a markdown file to point to processed versions.
    
    Args:
        markdown_path: Path to markdown file to update.
        attachment_metadata: Dictionary mapping original paths to metadata.
    """
    if not markdown_path.exists():
        return
        
    # Read markdown content
    content = markdown_path.read_text()
    
    # Regular expressions for finding links
    link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    
    def replace_link(match: re.Match) -> str:
        """Replace a link with its processed version."""
        text, path = match.groups()
        
        # Skip external links
        if path.startswith(('http://', 'https://', 'ftp://')):
            return match.group(0)
            
        # Convert path to absolute
        abs_path = str(Path(path).resolve())
        
        # Look up metadata for path
        metadata = attachment_metadata.get(abs_path)
        if not metadata or not metadata.output_path:
            return match.group(0)
            
        # Create relative path from markdown to output
        rel_path = Path(os.path.relpath(
            metadata.output_path,
            markdown_path.parent
        ))
        
        return f'[{text}]({rel_path})'
    
    def replace_image(match: re.Match) -> str:
        """Replace an image link with its processed version."""
        alt_text, path = match.groups()
        
        # Skip external images
        if path.startswith(('http://', 'https://', 'ftp://')):
            return match.group(0)
            
        # Convert path to absolute
        abs_path = str(Path(path).resolve())
        
        # Look up metadata for path
        metadata = attachment_metadata.get(abs_path)
        if not metadata or not metadata.output_path:
            return match.group(0)
            
        # Create relative path from markdown to output
        rel_path = Path(os.path.relpath(
            metadata.output_path,
            markdown_path.parent
        ))
        
        return f'![{alt_text}]({rel_path})'
    
    # Update links and images
    content = re.sub(link_pattern, replace_link, content)
    content = re.sub(image_pattern, replace_image, content)
    
    # Write updated content
    markdown_path.write_text(content) 