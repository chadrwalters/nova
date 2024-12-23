"""Handler for consolidating markdown files."""

from typing import Any, Dict, List, Optional
from pathlib import Path
import re
from datetime import datetime

class ConsolidationHandler:
    """Handles consolidation of markdown files and their attachments."""
    
    def __init__(self, sort_by_date: bool = True, preserve_headers: bool = True):
        """Initialize consolidation handler.
        
        Args:
            sort_by_date: Whether to sort files by date
            preserve_headers: Whether to preserve file headers
        """
        self.sort_by_date = sort_by_date
        self.preserve_headers = preserve_headers
        self.date_pattern = re.compile(r'(\d{4})(\d{2})(\d{2})')
        
    def extract_date(self, filename: str) -> Optional[datetime]:
        """Extract date from filename.
        
        Args:
            filename: Filename to extract date from
            
        Returns:
            Extracted date or None if not found
        """
        match = self.date_pattern.search(filename)
        if match:
            year, month, day = match.groups()
            try:
                return datetime(int(year), int(month), int(day))
            except ValueError:
                return None
        return None
        
    def sort_files(self, files: List[Path]) -> List[Path]:
        """Sort files by date if enabled.
        
        Args:
            files: List of files to sort
            
        Returns:
            Sorted list of files
        """
        if not self.sort_by_date:
            return sorted(files)
            
        def sort_key(file: Path) -> tuple:
            date = self.extract_date(file.name)
            return (date or datetime.max, file.name)
            
        return sorted(files, key=sort_key)
        
    def process_file(self, file_path: Path, output_path: Path) -> Dict[str, Any]:
        """Process a single markdown file.
        
        Args:
            file_path: Path to input file
            output_path: Path to output file
            
        Returns:
            Processing statistics
        """
        stats = {
            'file': file_path.name,
            'size': file_path.stat().st_size,
            'attachments': 0,
            'images': 0,
            'errors': []
        }
        
        try:
            # Read input file
            content = file_path.read_text(encoding='utf-8')
            
            # Add file header if enabled
            if self.preserve_headers:
                header = f"# {file_path.stem}\n\n"
                content = header + content
                
            # Write processed content
            output_path.write_text(content, encoding='utf-8')
            
        except Exception as e:
            stats['errors'].append(str(e))
            
        return stats
        
    def consolidate_files(self, input_files: List[Path], output_dir: Path) -> Dict[str, Any]:
        """Consolidate multiple markdown files.
        
        Args:
            input_files: List of input files
            output_dir: Output directory
            
        Returns:
            Consolidation statistics
        """
        stats = {
            'total_files': len(input_files),
            'total_size': 0,
            'processed_files': [],
            'errors': []
        }
        
        # Sort files
        sorted_files = self.sort_files(input_files)
        
        # Process each file
        for file_path in sorted_files:
            output_path = output_dir / file_path.name
            file_stats = self.process_file(file_path, output_path)
            
            stats['total_size'] += file_stats['size']
            stats['processed_files'].append(file_stats)
            if file_stats['errors']:
                stats['errors'].extend(file_stats['errors'])
                
        return stats 