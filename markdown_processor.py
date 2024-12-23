#!/usr/bin/env python3

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import markdown
import chardet
from bs4 import BeautifulSoup
from attachment_processor import create_processor

class MarkdownProcessor:
    """Processes markdown files and their embedded content."""
    
    def __init__(self, input_dir: Path, output_dir: Path, temp_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.temp_dir = temp_dir
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Create file handler
        log_file = output_dir / "markdown_processor.log"
        fh = logging.FileHandler(str(log_file))
        fh.setLevel(logging.DEBUG)
        
        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
        # Initialize markdown parser with extensions
        self.md = markdown.Markdown(extensions=[
            'markdown.extensions.tables',
            'markdown.extensions.fenced_code',
            'markdown.extensions.footnotes',
            'markdown.extensions.attr_list',
            'markdown.extensions.def_list',
            'markdown.extensions.abbr',
            'markdown.extensions.meta'
        ])
    
    def process_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Process a single markdown file and its attachments."""
        try:
            self.logger.info(f"Processing markdown file: {file_path}")
            
            # Read file content with proper encoding
            content = self._read_file_with_encoding(file_path)
            if not content:
                return None
            
            # Convert markdown to HTML
            html = self.md.convert(content)
            
            # Parse HTML to find attachments
            soup = BeautifulSoup(html, 'html.parser')
            
            # Process attachments
            attachments = self._process_attachments(soup, file_path)
            
            # Update markdown content with processed attachments
            updated_content = self._update_content_with_attachments(content, attachments)
            
            # Save processed file
            output_path = self._get_output_path(file_path)
            self._save_processed_file(output_path, updated_content)
            
            return {
                'input_file': str(file_path),
                'output_file': str(output_path),
                'attachments': attachments
            }
        
        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {str(e)}")
            return None
    
    def _read_file_with_encoding(self, file_path: Path) -> Optional[str]:
        """Read file content with proper encoding detection."""
        try:
            with open(file_path, 'rb') as f:
                raw_content = f.read()
                result = chardet.detect(raw_content)
                encoding = result['encoding'] or 'utf-8'
                return raw_content.decode(encoding)
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {str(e)}")
            return None
    
    def _process_attachments(self, soup: BeautifulSoup, source_file: Path) -> List[Dict[str, Any]]:
        """Process all attachments found in the markdown content."""
        attachments = []
        
        # Process images
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src:
                attachment_path = self._resolve_attachment_path(src, source_file)
                if attachment_path and attachment_path.exists():
                    processor = create_processor(attachment_path, self.output_dir)
                    if processor:
                        markdown_content = processor.process()
                        if markdown_content:
                            attachments.append({
                                'type': 'image',
                                'original_path': str(attachment_path),
                                'markdown_content': markdown_content
                            })
        
        # Process links to attachments
        for link in soup.find_all('a'):
            href = link.get('href', '')
            if href:
                attachment_path = self._resolve_attachment_path(href, source_file)
                if attachment_path and attachment_path.exists():
                    processor = create_processor(attachment_path, self.output_dir)
                    if processor:
                        markdown_content = processor.process()
                        if markdown_content:
                            # Determine attachment type based on file extension
                            ext = attachment_path.suffix.lower()
                            if ext in ['.pdf']:
                                attachment_type = 'pdf'
                            elif ext in ['.docx', '.doc']:
                                attachment_type = 'document'
                            elif ext in ['.xlsx', '.xls', '.csv']:
                                attachment_type = 'spreadsheet'
                            else:
                                attachment_type = 'link'
                            
                            attachments.append({
                                'type': attachment_type,
                                'original_path': str(attachment_path),
                                'markdown_content': markdown_content
                            })
        
        return attachments
    
    def _resolve_attachment_path(self, path: str, source_file: Path) -> Optional[Path]:
        """Resolve the actual path of an attachment."""
        try:
            # Check if path is absolute
            if os.path.isabs(path):
                return Path(path)
            
            # Try relative to source file
            relative_path = source_file.parent / path
            if relative_path.exists():
                return relative_path
            
            # Try relative to input directory
            input_path = self.input_dir / path
            if input_path.exists():
                return input_path
            
            return None
        except Exception as e:
            self.logger.error(f"Error resolving path {path}: {str(e)}")
            return None
    
    def _update_content_with_attachments(self, content: str, attachments: List[Dict[str, Any]]) -> str:
        """Update the markdown content with processed attachments."""
        updated_content = content
        
        for attachment in attachments:
            # Add attachment marker and content
            marker = f"\n\n--==ATTACHMENT_BLOCK: {attachment['original_path']}==--\n"
            marker += attachment['markdown_content']
            marker += "\n--==ATTACHMENT_BLOCK_END==--\n\n"
            
            # Add marker at the end of the content
            updated_content += marker
        
        return updated_content
    
    def _get_output_path(self, input_path: Path) -> Path:
        """Get the output path for a processed file."""
        relative_path = input_path.relative_to(self.input_dir)
        return self.output_dir / relative_path
    
    def _save_processed_file(self, output_path: Path, content: str):
        """Save the processed file."""
        try:
            # Create parent directories if they don't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save the file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.info(f"Saved processed file: {output_path}")
        except Exception as e:
            self.logger.error(f"Error saving file {output_path}: {str(e)}")
    
    def process_directory(self) -> bool:
        """Process all markdown files in the input directory."""
        try:
            # Find all markdown files
            markdown_files = list(self.input_dir.glob('**/*.md'))
            self.logger.info(f"Found {len(markdown_files)} markdown files")
            
            # Process each file
            success = True
            for file_path in markdown_files:
                result = self.process_file(file_path)
                if not result:
                    success = False
            
            return success
        except Exception as e:
            self.logger.error(f"Error processing directory: {str(e)}")
            return False 