"""Markdown processor for converting documents to markdown format."""

import os
from pathlib import Path
from typing import Dict, Any
import re

def _validate_links(content: str, source_file: Path) -> Dict[str, Any]:
    """Validate links in markdown content.
    
    Args:
        content: Markdown content to validate
        source_file: Source file path for resolving relative links
        
    Returns:
        Dictionary containing validation results
    """
    validation_info = {
        'is_valid': True,
        'errors': [],
        'warnings': []
    }
    
    try:
        # Find all links
        link_pattern = r'\[([^\]]*)\]\(([^)]+)\)'
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        
        # Check for broken links
        for match in re.finditer(link_pattern, content):
            link_url = match.group(2)
            if not link_url.startswith(('http://', 'https://', 'mailto:', 'tel:')):
                try:
                    link_path = Path(source_file.parent) / link_url
                    if not link_path.exists():
                        validation_info['warnings'].append(f"Broken link: {link_url}")
                except Exception as e:
                    validation_info['warnings'].append(f"Invalid link path {link_url}: {str(e)}")
        
        # Check for broken images
        for match in re.finditer(image_pattern, content):
            image_url = match.group(2)
            if not image_url.startswith(('http://', 'https://', 'data:')):
                try:
                    image_path = Path(source_file.parent) / image_url
                    if not image_path.exists():
                        validation_info['warnings'].append(f"Broken image: {image_url}")
                except Exception as e:
                    validation_info['warnings'].append(f"Invalid image path {image_url}: {str(e)}")
        
        return validation_info
        
    except Exception as e:
        validation_info['errors'].append(f"Link validation failed: {str(e)}")
        validation_info['is_valid'] = False
        return validation_info 