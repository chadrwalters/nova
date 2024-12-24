"""Handler for aggregating multiple markdown files into one."""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
import aiofiles

from .base_handler import BaseAggregateHandler
from ..config.defaults import DEFAULT_CONFIG

class AggregateHandler(BaseAggregateHandler):
    """Handles aggregation of multiple markdown files into one."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the aggregation handler.
        
        Args:
            config: Optional configuration overrides
        """
        super().__init__(config)
        
        # Merge default config with provided config
        self.config = {**DEFAULT_CONFIG.get('aggregate', {}), **(config or {})}
        
        # Set up markers
        self.markers = self.config.get('section_markers', {
            'start': '<!-- START_FILE: {filename} -->',
            'end': '<!-- END_FILE: {filename} -->',
            'separator': '\n---\n'
        })
        
        # Initialize tracking
        self.processed_files: Set[Path] = set()
    
    def can_handle(self, files: List[Path]) -> bool:
        """Check if files can be aggregated.
        
        Args:
            files: List of files to check
            
        Returns:
            bool: True if files are markdown and can be aggregated
        """
        return all(f.suffix.lower() == '.md' for f in files)
    
    async def process(self, files: List[Path], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process and aggregate markdown files.
        
        Args:
            files: List of files to aggregate
            context: Processing context
            
        Returns:
            Dict containing aggregation results
        """
        result = {
            'content': '',
            'metadata': {
                'files': [],
                'total_files': len(files),
                'created_at': datetime.now().isoformat(),
                'sections': {}
            },
            'file_map': {},
            'errors': []
        }
        
        try:
            # Sort files if needed
            sorted_files = self._sort_files(files)
            
            # Process each file
            sections = []
            for file_path in sorted_files:
                try:
                    if file_path in self.processed_files:
                        continue
                        
                    section = await self._process_file(file_path, context)
                    if section:
                        sections.append(section)
                        result['metadata']['files'].append(str(file_path))
                        result['file_map'][str(file_path)] = len(sections) - 1
                        result['metadata']['sections'][str(file_path)] = {
                            'index': len(sections) - 1,
                            'title': section.get('title', ''),
                            'size': len(section['content'])
                        }
                        
                        self.processed_files.add(file_path)
                        
                except Exception as e:
                    result['errors'].append(f"Error processing file {file_path}: {str(e)}")
            
            # Combine sections
            result['content'] = await self._combine_sections(sections)
            
            # Add table of contents if configured
            if self.config.get('add_table_of_contents', True):
                toc = self._generate_toc(sections)
                result['content'] = toc + self.markers['separator'] + result['content']
            
        except Exception as e:
            result['errors'].append(f"Error during aggregation: {str(e)}")
            await self.rollback(result)
        
        return result
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate processing results.
        
        Args:
            result: Processing results to validate
            
        Returns:
            bool: True if results are valid
        """
        required_keys = {'content', 'metadata', 'file_map', 'errors'}
        return (
            all(key in result for key in required_keys) and
            isinstance(result['content'], str) and
            isinstance(result['metadata'], dict) and
            isinstance(result['file_map'], dict) and
            isinstance(result['errors'], list) and
            'files' in result['metadata'] and
            'sections' in result['metadata']
        )
    
    async def rollback(self, result: Dict[str, Any]) -> None:
        """Rollback is not needed for aggregation as it's non-destructive."""
        pass
    
    def _sort_files(self, files: List[Path]) -> List[Path]:
        """Sort files according to configuration."""
        sort_by = self.config.get('sort_by', 'name')
        reverse = self.config.get('sort_reverse', False)
        
        if sort_by == 'name':
            return sorted(files, reverse=reverse)
        elif sort_by == 'modified':
            return sorted(files, key=lambda f: f.stat().st_mtime, reverse=reverse)
        elif sort_by == 'size':
            return sorted(files, key=lambda f: f.stat().st_size, reverse=reverse)
        else:
            return files
    
    async def _process_file(self, file_path: Path, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single file.
        
        Returns:
            Dict containing section info or None if processing failed
        """
        try:
            content = await self._read_file(file_path)
            
            # Extract title from first heading
            title = self._extract_title(content) or file_path.stem
            
            return {
                'title': title,
                'content': self._wrap_content(content, file_path),
                'file_path': str(file_path),
                'metadata': {
                    'size': len(content),
                    'modified': file_path.stat().st_mtime
                }
            }
            
        except Exception as e:
            print(f"Error processing file {file_path}: {str(e)}")
            return None
    
    async def _read_file(self, file_path: Path) -> str:
        """Read file content."""
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            return await f.read()
    
    def _extract_title(self, content: str) -> Optional[str]:
        """Extract title from first heading in content."""
        heading_pattern = r'^#\s+(.+)$'
        match = re.search(heading_pattern, content, re.MULTILINE)
        return match.group(1) if match else None
    
    def _wrap_content(self, content: str, file_path: Path) -> str:
        """Wrap content with section markers."""
        return (
            f"{self.markers['start'].format(filename=file_path.name)}\n"
            f"{content.strip()}\n"
            f"{self.markers['end'].format(filename=file_path.name)}"
        )
    
    async def _combine_sections(self, sections: List[Dict[str, Any]]) -> str:
        """Combine all sections into final content."""
        separator = self.markers['separator']
        return separator.join(
            section['content']
            for section in sections
        )
    
    def _generate_toc(self, sections: List[Dict[str, Any]]) -> str:
        """Generate table of contents."""
        toc = ["# Table of Contents\n"]
        
        for i, section in enumerate(sections, 1):
            title = section['title']
            file_path = section['file_path']
            toc.append(f"{i}. [{title}](#{self._make_anchor(title)})")
        
        return '\n'.join(toc)
    
    def _make_anchor(self, title: str) -> str:
        """Convert title to HTML anchor."""
        return re.sub(r'[^\w\s-]', '', title).lower().replace(' ', '-') 