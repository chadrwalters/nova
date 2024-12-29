"""Spreadsheet file handler."""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Union
import shutil

import pandas as pd
import chardet

from ..models.document import DocumentMetadata
from .base import BaseHandler
from ..config.manager import ConfigManager


class SpreadsheetHandler(BaseHandler):
    """Handler for spreadsheet files."""
    
    name = "spreadsheet"
    version = "0.1.0"
    file_types = ["xlsx", "xls", "csv", "ods"]
    
    def __init__(self, config: ConfigManager) -> None:
        """Initialize spreadsheet handler.
        
        Args:
            config: Nova configuration manager.
        """
        super().__init__(config)
    
    async def _process_content(self, file_path: Path) -> str:
        """Process spreadsheet file content.
        
        Args:
            file_path: Path to file.
            
        Returns:
            Processed content.
        """
        try:
            if file_path.suffix.lower() in ['.xlsx', '.xls', '.ods']:
                # Read Excel file
                df = pd.read_excel(file_path)
                return df.to_markdown(index=False, tablefmt="pipe")
                
            elif file_path.suffix.lower() == '.csv':
                try:
                    # First try UTF-8
                    df = pd.read_csv(file_path, encoding='utf-8')
                    return df.to_markdown(index=False, tablefmt="pipe")
                except UnicodeDecodeError:
                    # If UTF-8 fails, try to detect encoding
                    with open(file_path, 'rb') as f:
                        raw_data = f.read()
                        result = chardet.detect(raw_data)
                        if result['encoding']:
                            try:
                                df = pd.read_csv(file_path, encoding=result['encoding'])
                                return df.to_markdown(index=False, tablefmt="pipe")
                            except:
                                pass
                    
                    # If all else fails, create warning message
                    return f"""# Warning: Encoding Issue

The CSV file could not be processed due to encoding issues.

## Recommendations
1. Try opening the file in Excel or another spreadsheet program
2. Save it with UTF-8 encoding"""
                    
            else:
                raise ValueError(f"Unsupported file type: {file_path.suffix}")
                
        except Exception as e:
            return f"Error processing spreadsheet: {str(e)}" 
    
    def _write_markdown(self, output_path: Path, title: str, file_path: Path, content: str) -> bool:
        """Write markdown file with spreadsheet content.
        
        Args:
            output_path: Path to write markdown file.
            title: Title for markdown file.
            file_path: Path to original file.
            content: Processed content.
            
        Returns:
            True if file was written, False if unchanged.
        """
        markdown_content = f"""# {title}

## Content

{content}
"""
        return self._safe_write_file(output_path, markdown_content)
    
    async def process_impl(
        self,
        file_path: Path,
        metadata: DocumentMetadata,
    ) -> Optional[DocumentMetadata]:
        """Process a spreadsheet file.
        
        Args:
            file_path: Path to file.
            metadata: Document metadata.
                
        Returns:
            Document metadata, or None if file is ignored.
            
        Raises:
            ValueError: If file cannot be processed.
        """
        try:
            # Get output path from output manager
            output_path = self.output_manager.get_output_path_for_phase(
                file_path,
                "parse",
                ".parsed.md"
            )
            
            # Process content
            content = await self._process_content(file_path)
            
            # Write markdown file
            was_written = self._write_markdown(output_path, file_path.stem, file_path, content)
            
            # Update metadata
            metadata.title = file_path.stem
            metadata.metadata['original_path'] = str(file_path)
            metadata.processed = True
            metadata.unchanged = not was_written
            metadata.add_output_file(output_path)
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to process spreadsheet {file_path}: {str(e)}")
            metadata.add_error(self.name, str(e))
            return metadata 
    
    def _convert_excel_to_markdown(self, file_path: Path) -> str:
        """Convert Excel file to markdown table.
        
        Args:
            file_path: Path to Excel file.
            
        Returns:
            Markdown table representation of Excel file.
        """
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Convert to markdown table
            return df.to_markdown(index=False)
            
        except Exception as e:
            return f"Error converting Excel to markdown: {str(e)}"
            
    def _convert_csv_to_markdown(self, file_path: Path) -> str:
        """Convert CSV file to markdown table.
        
        Args:
            file_path: Path to CSV file.
            
        Returns:
            Markdown table representation of CSV file.
        """
        try:
            # Read CSV file
            df = pd.read_csv(file_path)
            
            # Convert to markdown table
            return df.to_markdown(index=False)
            
        except Exception as e:
            return f"Error converting CSV to markdown: {str(e)}" 