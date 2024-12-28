"""Metadata manager for handling document metadata operations."""

# Standard library imports
import json
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple

# Nova package imports
from nova.core.logging import get_logger

logger = get_logger(__name__)

class MetadataManager:
    """Manages metadata operations for markdown documents."""
    
    def __init__(self):
        """Initialize metadata manager."""
        self.logger = logger
    
    def extract_metadata(self, content: str) -> Tuple[Dict[str, Any], str]:
        """Extract metadata from content.
        
        Args:
            content: Content to extract metadata from
            
        Returns:
            Tuple of (metadata dict, remaining content)
            
        Raises:
            json.JSONDecodeError: If metadata is invalid JSON
        """
        if not content:
            return {}, ""
        
        # Split content into lines
        content_lines = content.splitlines()
        metadata = {}
        content_start = 0
        
        # Look for metadata in HTML comment
        if content_lines and content_lines[0].strip().startswith('<!--'):
            metadata_lines = []
            for i, line in enumerate(content_lines):
                if line.strip().endswith('-->'):
                    # Extract metadata string
                    metadata_str = ' '.join(
                        line.strip() for line in content_lines[:i+1]
                        if not line.strip().startswith('<!--') and not line.strip().endswith('-->')
                    )
                    try:
                        metadata = json.loads(metadata_str)
                        content_start = i + 1
                        break
                    except json.JSONDecodeError:
                        # If metadata parsing fails, try next line
                        continue
        
        # Extract content sections
        sections = {
            'summary_blocks': [],
            'raw_notes_blocks': [],
            'attachment_blocks': []
        }
        
        current_section = None
        current_block = []
        
        for line in content_lines[content_start:]:
            # Check for section markers
            if '--==SUMMARY==--' in line:
                if current_block and current_section:
                    sections[current_section].append('\n'.join(current_block))
                current_section = 'summary_blocks'
                current_block = []
                continue
            elif '--==RAW NOTES==--' in line or '--==RAW_NOTES==--' in line:
                if current_block and current_section:
                    sections[current_section].append('\n'.join(current_block))
                current_section = 'raw_notes_blocks'
                current_block = []
                continue
            elif '--==ATTACHMENTS==--' in line:
                if current_block and current_section:
                    sections[current_section].append('\n'.join(current_block))
                current_section = 'attachment_blocks'
                current_block = []
                continue
            elif '--==ATTACHMENT_BLOCK:' in line:
                if current_block and current_section:
                    sections[current_section].append('\n'.join(current_block))
                current_section = 'attachment_blocks'
                current_block = [line]
                continue
            elif '--==ATTACHMENT_BLOCK_END==--' in line:
                if current_block:
                    current_block.append(line)
                    sections['attachment_blocks'].append('\n'.join(current_block))
                current_block = []
                continue
            elif current_section:
                current_block.append(line)
            else:
                # Default to raw_notes if no section is identified
                if not current_section:
                    current_section = 'raw_notes_blocks'
                current_block.append(line)
        
        # Add any remaining block
        if current_block and current_section:
            sections[current_section].append('\n'.join(current_block))
        
        # Update metadata with content markers
        if 'content_markers' not in metadata:
            metadata['content_markers'] = {}
        metadata['content_markers'].update(sections)
        
        # Return metadata and remaining content
        return metadata, '\n'.join(content_lines[content_start:])
    
    def merge_metadata(self, metadata_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple metadata dictionaries.
        
        Args:
            metadata_list: List of metadata dictionaries to merge
            
        Returns:
            Merged metadata dictionary
        """
        if not metadata_list:
            return {}
            
        merged = {
            'document': {
                'processor': 'MetadataManager',
                'version': '1.0',
                'timestamp': datetime.now().isoformat(),
                'total_files': len(metadata_list)
            },
            'structure': {
                'files': [],
                'section_order': ['summary', 'raw_notes', 'attachments']
            },
            'relationships': {
                'attachments': [],
                'references': [],
                'dependencies': []
            },
            'content_markers': {
                'summary_blocks': [],
                'raw_notes_blocks': [],
                'attachment_blocks': []
            }
        }
        
        for metadata in metadata_list:
            # Merge document info
            if 'document' in metadata:
                merged['document'].update({
                    k: v for k, v in metadata['document'].items()
                    if k not in ['processor', 'version', 'timestamp']
                })
            
            # Track file in structure
            if 'document' in metadata and 'file' in metadata['document']:
                merged['structure']['files'].append({
                    'path': metadata['document']['file'],
                    'sequence': len(merged['structure']['files']) + 1
                })
            
            # Merge relationships
            if 'relationships' in metadata:
                for key in ['attachments', 'references', 'dependencies']:
                    if key in metadata['relationships']:
                        merged['relationships'][key].extend(metadata['relationships'][key])
            
            # Merge content markers
            if 'content_markers' in metadata:
                for key in ['summary_blocks', 'raw_notes_blocks', 'attachment_blocks']:
                    if key in metadata['content_markers']:
                        merged['content_markers'][key].extend(metadata['content_markers'][key])
        
        # Remove duplicates while preserving order
        for key in ['attachments', 'references', 'dependencies']:
            merged['relationships'][key] = list({
                json.dumps(item): item 
                for item in merged['relationships'][key]
            }.values())
        
        return merged
    
    def validate_metadata(self, metadata: Dict[str, Any]) -> List[str]:
        """Validate metadata structure.
        
        Args:
            metadata: Metadata dictionary to validate
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Check required top-level sections
        required_sections = ['document', 'structure', 'relationships', 'content_markers']
        for section in required_sections:
            if section not in metadata:
                errors.append(f"Missing required section: {section}")
        
        # Validate document section
        if 'document' in metadata:
            required_doc_fields = ['processor', 'version', 'timestamp']
            for field in required_doc_fields:
                if field not in metadata['document']:
                    errors.append(f"Missing required document field: {field}")
        
        # Validate structure section
        if 'structure' in metadata:
            if 'files' not in metadata['structure']:
                errors.append("Missing files list in structure")
            if 'section_order' not in metadata['structure']:
                errors.append("Missing section_order in structure")
        
        # Validate relationships section
        if 'relationships' in metadata:
            required_rel_fields = ['attachments', 'references', 'dependencies']
            for field in required_rel_fields:
                if field not in metadata['relationships']:
                    errors.append(f"Missing required relationships field: {field}")
        
        # Validate content markers section
        if 'content_markers' in metadata:
            required_marker_fields = ['summary_blocks', 'raw_notes_blocks', 'attachment_blocks']
            for field in required_marker_fields:
                if field not in metadata['content_markers']:
                    errors.append(f"Missing required content_markers field: {field}")
        
        return errors
    
    def serialize_metadata(self, metadata: Dict[str, Any]) -> str:
        """Serialize metadata to HTML comment format.
        
        Args:
            metadata: Metadata dictionary to serialize
            
        Returns:
            Metadata formatted as HTML comment
        """
        try:
            # Ensure all values are JSON serializable
            def clean_value(v):
                if isinstance(v, (datetime, date)):
                    return v.isoformat()
                elif isinstance(v, Path):
                    return str(v)
                return v

            cleaned_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, dict):
                    cleaned_metadata[key] = {k: clean_value(v) for k, v in value.items()}
                elif isinstance(value, list):
                    cleaned_metadata[key] = [clean_value(v) for v in value]
                else:
                    cleaned_metadata[key] = clean_value(value)

            metadata_json = json.dumps(cleaned_metadata, indent=2)
            return f"<!-- {metadata_json} -->\n"
        except Exception as e:
            self.logger.error(f"Failed to serialize metadata: {str(e)}")
            self.logger.error(f"Problematic metadata: {metadata}")
            return "<!-- {} -->\n"
    
    def get_section_content(self, metadata: Dict[str, Any], section_type: str) -> List[Dict[str, Any]]:
        """Get content blocks for a specific section type.
        
        Args:
            metadata: Metadata dictionary
            section_type: Type of section (summary, raw_notes, attachment)
            
        Returns:
            List of content blocks for the section
        """
        if 'content_markers' not in metadata:
            return []
            
        marker_key = f"{section_type}_blocks"
        if marker_key not in metadata['content_markers']:
            return []
            
        return metadata['content_markers'][marker_key] 