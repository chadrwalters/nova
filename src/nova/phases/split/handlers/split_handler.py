"""Handler for splitting aggregated markdown content."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import aiofiles

from ....core.logging import get_logger
from ....core.file_ops import FileOperationsManager
from ....models.parsed_result import ParsedResult

logger = get_logger(__name__)

class SplitHandler:
    """Handler for splitting aggregated markdown content."""
    
    def __init__(self, config: dict):
        """Initialize split handler.
        
        Args:
            config: Configuration dictionary
        """
        self.output_files = config.get('output_files', {})
        self.section_markers = config.get('section_markers', {})
        self.attachment_markers = config.get('attachment_markers', {})
        self.content_type_rules = config.get('content_type_rules', {})
        self.content_preservation = config.get('content_preservation', {})
        self.cross_linking = config.get('cross_linking', True)
        self.preserve_headers = config.get('preserve_headers', True)
        self.file_ops = FileOperationsManager()
        
    async def setup(self):
        """Initialize the handler"""
        await self._setup_directories()
        
    async def _setup_directories(self):
        """Create necessary output directories"""
        for output_file in self.output_files.values():
            output_path = Path(output_file).parent
            if not output_path.exists():
                output_path.mkdir(parents=True, exist_ok=True)
                
    async def process_file(self, file_path: Path) -> bool:
        """Process a single file by splitting it into sections"""
        try:
            content = await self.file_ops.read_file(file_path)
            if not content:
                return False
                
            sections = self._split_content(content)
            await self._write_sections(sections)
            return True
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {str(e)}")
            return False
            
    def _split_content(self, content: str) -> dict:
        """Split content into sections based on markers"""
        sections = {
            'summary': [],
            'raw_notes': [],
            'attachments': []
        }
        
        current_section = None
        for line in content.split('\n'):
            # Check if line contains any section marker
            for section_name, marker in self.section_markers.items():
                if marker in line:
                    current_section = section_name
                    break
            else:  # No marker found, append to current section if one is active
                if current_section:
                    sections[current_section].append(line)
                
        return sections
        
    async def _write_sections(self, sections: dict):
        """Write sections to their respective files"""
        for section_name, content in sections.items():
            if not content:
                continue
                
            output_file = self.output_files.get(section_name)
            if not output_file:
                continue
                
            try:
                await self.file_ops.write_file(Path(output_file), '\n'.join(content))
            except Exception as e:
                logger.error(f"Failed to write {section_name} section: {str(e)}")
                
    async def cleanup(self):
        """Clean up resources."""
        pass 