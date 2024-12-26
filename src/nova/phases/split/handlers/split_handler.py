"""Handler for splitting aggregated markdown content."""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import aiofiles

from ....core.logging import get_logger
from ....core.file_ops import FileOperationsManager

logger = get_logger(__name__)

class SplitHandler:
    """Handler for splitting markdown content into sections."""
    
    def __init__(self, config: dict):
        """Initialize split handler.
        
        Args:
            config: Handler configuration
        """
        self.config = config
        self.output_files = config.get('output_files', {})
        self.section_markers = config.get('section_markers', {})
        self.file_ops = FileOperationsManager()
        
    @property
    def output_files(self) -> dict:
        """Get output files configuration."""
        return self._output_files
        
    @output_files.setter
    def output_files(self, value: dict):
        """Set output files configuration."""
        self._output_files = value
        
    async def setup(self):
        """Set up handler."""
        pass
        
    async def process_file(self, input_file: Path) -> bool:
        """Process a markdown file.
        
        Args:
            input_file: Path to input file
            
        Returns:
            True if processing was successful, False otherwise
        """
        try:
            # Read input file
            content = await self.file_ops.read_file(input_file)
            if not content:
                logger.error(f"Failed to read input file: {input_file}")
                return False
            
            # Extract metadata from HTML comment
            metadata = {}
            content_lines = []
            in_metadata = False
            metadata_json = ""
            
            for line in content.split('\n'):
                if line.strip().startswith('<!--'):
                    in_metadata = True
                    metadata_json = line.replace('<!--', '').strip()
                    continue
                elif in_metadata and line.strip().endswith('-->'):
                    metadata_json += line.replace('-->', '').strip()
                    try:
                        metadata = json.loads(metadata_json)
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse metadata JSON")
                    in_metadata = False
                    continue
                elif in_metadata:
                    metadata_json += line.strip()
                    continue
                content_lines.append(line)
            
            # Reconstruct content without metadata comment
            content = '\n'.join(content_lines)
            
            # Initialize sections
            sections = {
                'summary': [],
                'raw_notes': [],
                'attachments': []
            }
            
            # Use aggregated metadata to split content
            if metadata and 'sections' in metadata:
                # Get section order from metadata
                section_order = metadata.get('structure', {}).get('section_order', ['summary', 'raw_notes', 'attachments'])
                
                # Process each file in order
                for file_metadata in metadata.get('files', []):
                    file_path = file_metadata.get('path', '')
                    file_sections = file_metadata.get('sections', {})
                    
                    # Add content from each section
                    for section_name in section_order:
                        if section_name in file_sections and file_sections[section_name]:
                            sections[section_name].extend(file_sections[section_name])
                            sections[section_name].append('')  # Add separator
                            
                    # Add any section markers from the original metadata
                    if 'metadata' in file_metadata and 'content_markers' in file_metadata['metadata']:
                        markers = file_metadata['metadata']['content_markers']
                        for section_name in section_order:
                            marker_key = f"{section_name}_blocks"
                            if marker_key in markers:
                                for block in markers[marker_key]:
                                    if isinstance(block, dict) and 'content' in block:
                                        sections[section_name].extend(block['content'])
                                        sections[section_name].append('')
            else:
                # Fallback to marker-based splitting if no metadata
                logger.warning("No metadata found, falling back to marker-based splitting")
                sections = self._split_content(content)
            
            # Write sections to output files
            frontmatter = {}
            if metadata and 'files' in metadata and metadata['files']:
                # Use metadata from first file as default frontmatter
                first_file = metadata['files'][0]
                if 'metadata' in first_file and 'document' in first_file['metadata']:
                    frontmatter = first_file['metadata']['document'].get('frontmatter', {})
            
            await self._write_sections(sections, frontmatter)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to process file {input_file}: {str(e)}")
            return False
            
    def _split_content(self, content: str) -> dict:
        """Split content into sections."""
        sections = {
            'summary': [],
            'raw_notes': [],
            'attachments': []
        }
        
        # Extract metadata if present
        metadata_lines = []
        lines = content.splitlines()
        
        # Look for metadata block
        if lines and lines[0].startswith('<!--'):
            in_metadata = True
            for line in lines:
                if in_metadata:
                    metadata_lines.append(line)
                    if '-->' in line:
                        in_metadata = False
                        break
            
            # Validate metadata format
            metadata_str = '\n'.join(metadata_lines)
            if not metadata_str.endswith('-->'):
                raise ValueError("Invalid metadata block: missing closing marker")
            
            try:
                metadata_json = metadata_str[4:-3].strip()  # Remove <!-- and -->
                json.loads(metadata_json)  # Validate JSON
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid metadata JSON: {str(e)}")
            
            # Remove metadata lines from content
            lines = lines[len(metadata_lines):]
        
        # Look for section markers
        section_boundaries = []
        for i, line in enumerate(lines):
            if '--==SUMMARY==--' in line:
                section_boundaries.append((i, 'summary'))
            elif '--==RAW NOTES==--' in line or '--==RAW_NOTES==--' in line:
                section_boundaries.append((i, 'raw_notes'))
            elif '--==ATTACHMENTS==--' in line:
                section_boundaries.append((i, 'attachments'))
        
        # If no sections found, analyze content to determine type
        if not section_boundaries:
            content_type = self._analyze_content_type('\n'.join(lines))
            if metadata_lines:
                sections[content_type].extend(metadata_lines)
                sections[content_type].append('')
            sections[content_type].extend(lines)
            
            # Ensure all sections exist
            for section in sections:
                if not sections[section]:
                    sections[section] = []
            
            return sections
        
        # Sort boundaries by line number
        section_boundaries.sort()
        
        # Process each section
        for i in range(len(section_boundaries)):
            start_line, section_name = section_boundaries[i]
            # Get end line (either next section or end of file)
            end_line = section_boundaries[i + 1][0] if i + 1 < len(section_boundaries) else len(lines)
            
            # Get content between markers
            section_content = []
            for line in lines[start_line + 1:end_line]:
                # Skip section markers
                if any(marker in line for marker in ['--==SUMMARY==--', '--==RAW_NOTES==--', '--==ATTACHMENTS==--']):
                    continue
                section_content.append(line)
            
            # Clean up empty lines at start/end while preserving internal empty lines
            while section_content and not section_content[0].strip():
                section_content.pop(0)
            while section_content and not section_content[-1].strip():
                section_content.pop()
            
            # Add metadata and content to section
            if metadata_lines:
                sections[section_name].extend(metadata_lines)
                sections[section_name].append('')  # Add blank line after metadata
            sections[section_name].extend(section_content)
        
        # Ensure all sections exist
        for section in sections:
            if not sections[section]:
                sections[section] = []
        
        return sections
        
    def _analyze_content_type(self, content: str) -> str:
        """Analyze content to determine its type."""
        # Check for summary indicators
        summary_indicators = ['summary:', 'overview:', 'key points:', 'highlights:', 'executive summary']
        if any(indicator in content.lower() for indicator in summary_indicators):
            return 'summary'
        
        # Check for raw notes indicators
        raw_notes_indicators = ['notes:', 'log:', 'journal:', 'raw notes:', 'meeting notes']
        if any(indicator in content.lower() for indicator in raw_notes_indicators):
            return 'raw_notes'
        
        # Check for attachment indicators
        if '![' in content or '[download]' in content.lower() or any(ext in content.lower() for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip']):
            return 'attachments'
        
        # Default to raw notes if no clear indicators
        return 'raw_notes'
        
    async def _write_sections(self, sections: dict, metadata: dict = None):
        """Write sections to their respective files"""
        for section_name, content in sections.items():
            output_file = self.output_files.get(section_name)
            if not output_file:
                logger.warning(f"No output file configured for section: {section_name}")
                continue
                
            try:
                # Create parent directories
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Initialize final content
                final_content = []
                
                # Add metadata if present
                if metadata:
                    final_content.append('---')
                    for key, value in metadata.items():
                        if isinstance(value, (list, dict)):
                            final_content.append(f"{key}: {json.dumps(value)}")
                        else:
                            final_content.append(f"{key}: {value}")
                    final_content.append('---')
                    final_content.append('')
                
                # Add section content
                if isinstance(content, list):
                    final_content.extend(content)
                else:
                    final_content.append(str(content))
                
                # Clean up empty lines at start/end while preserving internal empty lines
                while final_content and not final_content[0].strip():
                    final_content.pop(0)
                while final_content and not final_content[-1].strip():
                    final_content.pop()
                
                # Ensure file has content
                if not final_content:
                    if section_name == 'summary':
                        final_content.extend(['# Summary', 'No summary content yet.'])
                    elif section_name == 'raw_notes':
                        final_content.extend(['# Raw Notes', 'No raw notes yet.'])
                    else:
                        final_content.extend([f'# {section_name.replace("_", " ").title()}', 'No content yet.'])
                
                # Write content
                await self.file_ops.write_file(output_path, '\n'.join(final_content))
                
            except Exception as e:
                logger.error(f"Failed to write {section_name} section: {str(e)}")
                raise
                
    async def cleanup(self):
        """Clean up resources."""
        pass 