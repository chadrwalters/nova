"""Markdown aggregation processor for merging consolidated markdown files."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
import re
import hashlib

from rich.console import Console

from .base import BaseProcessor
from ..core.config import NovaConfig, ProcessorConfig
from ..core.errors import ProcessingError
from ..core.logging import get_logger
from ..core.summary import ProcessingSummary

logger = logging.getLogger(__name__)
console = Console()

class MarkdownAggregateProcessor(BaseProcessor):
    """Processor for aggregating markdown files while preserving attachments."""
    
    def __init__(self, processor_config: ProcessorConfig, nova_config: NovaConfig):
        """Initialize processor."""
        super().__init__(processor_config, nova_config)
        self.logger = get_logger(self.__class__.__name__)
        
        # Get configuration
        aggregate_config = self.config.options.get('components', {}).get('aggregate_processor', {}).get('config', {})
        
        if not aggregate_config:
            self.logger.error("Missing aggregate_processor configuration")
            raise ProcessingError("Missing aggregate_processor configuration")
            
        self.output_filename = aggregate_config.get('output_filename', 'all_merged_markdown.md')
        self.include_file_headers = aggregate_config.get('include_file_headers', True)
        self.add_separators = aggregate_config.get('add_separators', True)
        
        # Get attachment markers from config
        consolidate_config = self.config.options.get('components', {}).get('consolidate_processor', {}).get('config', {})
        if not consolidate_config or "attachment_markers" not in consolidate_config:
            self.logger.error("Missing attachment marker configuration")
            raise ProcessingError("Missing attachment marker configuration")
            
        self.attachment_start = consolidate_config["attachment_markers"]["start"]
        self.attachment_end = consolidate_config["attachment_markers"]["end"]
        
        # Track seen headers and content hashes
        self.seen_headers = set()
        self.seen_content_hashes = set()
        
    def _setup(self) -> None:
        """Setup processor requirements."""
        # Initialize stats
        self.stats = {
            'files_processed': 0,
            'errors': 0,
            'warnings': 0,
            'duplicate_headers': 0,
            'duplicate_content': 0,
            'attachments_processed': 0
        }
        
        # Ensure output directory exists
        output_dir = Path(self.nova_config.paths.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_content_hash(self, content: str) -> str:
        """Generate a hash for content to detect duplicates."""
        # Normalize content by removing whitespace and converting to lowercase
        normalized = re.sub(r'\s+', ' ', content.lower()).strip()
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]
    
    def _is_duplicate_content(self, content: str) -> bool:
        """Check if content is a duplicate."""
        content_hash = self._get_content_hash(content)
        if content_hash in self.seen_content_hashes:
            return True
        self.seen_content_hashes.add(content_hash)
        return False
    
    def _clean_header(self, header: str) -> str:
        """Clean and normalize a header."""
        return re.sub(r'\s+', ' ', header.lower()).strip()
    
    def _is_duplicate_header(self, header: str) -> bool:
        """Check if header is a duplicate."""
        cleaned_header = self._clean_header(header)
        if cleaned_header in self.seen_headers:
            return True
        self.seen_headers.add(cleaned_header)
        return False
    
    def _extract_sections(self, content: str) -> Dict[str, List[str]]:
        """Extract content sections while removing duplicates."""
        sections = {
            'summary': [],
            'raw_notes': [],
            'attachments': set()
        }
        
        # Extract attachment blocks first
        attachment_pattern = re.compile(
            r'(--==ATTACHMENT_BLOCK: [^=]+==--.*?--==ATTACHMENT_BLOCK_END==--)',
            re.DOTALL
        )
        attachments = attachment_pattern.findall(content)
        for attachment in attachments:
            sections['attachments'].add(attachment)
        
        # Remove attachment blocks from content for further processing
        content = attachment_pattern.sub('', content)
        
        # Split into lines for processing
        lines = content.split('\n')
        current_section = 'raw_notes'
        buffer = []
        
        for line in lines:
            # Check for section markers
            if '--==SUMMARY==--' in line:
                current_section = 'summary'
                continue
            elif '--==RAW NOTES==--' in line:
                if buffer and not self._is_duplicate_content('\n'.join(buffer)):
                    sections[current_section].append('\n'.join(buffer))
                buffer = []
                current_section = 'raw_notes'
                continue
            
            # Check for headers
            header_match = re.match(r'^(#+)\s+(.+)$', line)
            if header_match:
                # Process previous buffer
                if buffer and not self._is_duplicate_content('\n'.join(buffer)):
                    sections[current_section].append('\n'.join(buffer))
                buffer = []
                
                # Check for duplicate headers
                if not self._is_duplicate_header(header_match.group(2)):
                    buffer.append(line)
            else:
                buffer.append(line)
        
        # Add final buffer
        if buffer and not self._is_duplicate_content('\n'.join(buffer)):
            sections[current_section].append('\n'.join(buffer))
        
        return sections
    
    def _extract_attachment_blocks(self, content: str) -> Tuple[str, Dict[str, str]]:
        """Extract attachment blocks from content.
        
        Args:
            content: Content to extract blocks from
            
        Returns:
            Tuple of (cleaned content, dict of filename -> block content)
        """
        blocks = {}
        cleaned_content = content
        
        # Extract blocks using regex
        pattern = re.compile(
            r'--==ATTACHMENT_BLOCK:\s*([^=]+?)==--\n(.*?)--==ATTACHMENT_BLOCK_END==--',
            re.DOTALL
        )
        
        for match in pattern.finditer(content):
            filename = match.group(1).strip()
            block_content = match.group(2).strip()
            blocks[filename] = block_content
            
        # Remove blocks from content
        cleaned_content = pattern.sub('', cleaned_content).strip()
        
        return cleaned_content, blocks
    
    def _add_file_header(self, content: str, file_path: Path) -> str:
        """Add file header to content.
        
        Args:
            content: Content to add header to
            file_path: Path to file
            
        Returns:
            Content with header added
        """
        if not self.include_file_headers:
            return content
        
        header = f"\n## File: {file_path.name}\n\n"
        return header + content
    
    def _analyze_content(self, content: str) -> Dict[str, Any]:
        """Analyze content structure and type.
        
        Args:
            content: Content to analyze
            
        Returns:
            Dict with analysis results
        """
        analysis = {
            'structured': False,
            'chronological': False,
            'has_metadata': False,
            'has_attachments': False,
            'is_structured': False,  # Legacy field for backward compatibility
            'is_chronological': False,  # Legacy field for backward compatibility
            'metrics': {
                'lines': 0,
                'words': 0,
                'headers': 0,
                'lists': 0,
                'code_blocks': 0
            }
        }
        
        # Count basic metrics
        lines = content.split('\n')
        analysis['metrics']['lines'] = len(lines)
        analysis['metrics']['words'] = len(re.findall(r'\w+', content))
        
        # Check for headers
        headers = re.findall(r'^#+\s+.+$', content, re.MULTILINE)
        analysis['metrics']['headers'] = len(headers)
        
        # Check for lists
        lists = re.findall(r'^\s*[-*+]\s+.+$', content, re.MULTILINE)
        analysis['metrics']['lists'] = len(lists)
        
        # Check for code blocks
        code_blocks = re.findall(r'```.*?```', content, re.DOTALL)
        analysis['metrics']['code_blocks'] = len(code_blocks)
        
        # Determine content type
        analysis['structured'] = analysis['metrics']['headers'] > 0 or analysis['metrics']['lists'] > 0
        analysis['is_structured'] = analysis['structured']  # Legacy field
        analysis['chronological'] = bool(re.search(r'^\d{4}-\d{2}-\d{2}', content, re.MULTILINE))
        analysis['is_chronological'] = analysis['chronological']  # Legacy field
        analysis['has_metadata'] = bool(re.search(r'<!--\s*{.*?}\s*-->', content, re.DOTALL))
        analysis['has_attachments'] = '--==ATTACHMENT_BLOCK:' in content
        
        return analysis
    
    def process(self, input_files: List[Path], output_dir: Path) -> Path:
        """Process input files and aggregate content.
        
        Args:
            input_files: List of input files to process
            output_dir: Output directory
            
        Returns:
            Path to output file
        """
        output_file = output_dir / "all_merged_markdown.md"
        
        # Initialize sections
        summary_content = ["# Aggregated Markdown\n\n"]
        raw_notes_content = ["# Raw Notes\n\n"]
        attachments_content = ["# Attachments\n\n"]
        
        # Process each input file
        for file_path in input_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                
                # Extract attachments
                cleaned_content, attachments = self._extract_attachment_blocks(content)
                
                # Add file header if enabled
                if self.include_file_headers:
                    cleaned_content = self._add_file_header(cleaned_content, file_path)
                
                # Analyze content
                analysis = self._analyze_content(cleaned_content)
                
                # Distribute content based on analysis
                if analysis['structured']:
                    summary_content.append(cleaned_content)
                else:
                    raw_notes_content.append(cleaned_content)
                    
                # Add attachments
                for filename, block in attachments.items():
                    attachments_content.append(
                        f"--==ATTACHMENT_BLOCK: {filename}==--\n"
                        f"{block}\n"
                        f"--==ATTACHMENT_BLOCK_END==--\n"
                    )
                    
            except Exception as e:
                self.logger.error(f"Failed to process {file_path}: {str(e)}")
                continue
        
        # Combine sections with separators
        output_content = (
            '\n'.join(summary_content) + '\n\n---\n\n' +
            '\n'.join(raw_notes_content) + '\n\n---\n\n' +
            '\n'.join(attachments_content)
        )
        
        # Write output file
        output_file.write_text(output_content, encoding='utf-8')
        
        return output_file