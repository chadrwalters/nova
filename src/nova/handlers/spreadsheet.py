"""Spreadsheet file handler."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd

from ..models.document import DocumentMetadata
from .base import BaseHandler
from ..config.manager import ConfigManager


class SpreadsheetHandler(BaseHandler):
    """Handler for spreadsheet files."""
    
    name = "spreadsheet"
    version = "0.1.0"
    file_types = ["xlsx", "xls", "csv"]
    
    def __init__(self, config: ConfigManager) -> None:
        """Initialize spreadsheet handler.
        
        Args:
            config: Nova configuration manager.
        """
        super().__init__(config)
    
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
            
            # Process content based on file type
            if file_path.suffix.lower() in ['.xlsx', '.xls']:
                content = self._convert_excel_to_markdown(file_path)
            else:  # CSV
                content = self._convert_csv_to_markdown(file_path)
            
            # Update metadata
            metadata.title = file_path.stem
            metadata.metadata['original_path'] = str(file_path)
            metadata.processed = True
            
            # Write markdown using MarkdownWriter
            self.markdown_writer.write_document(
                title=metadata.title,
                content=content,
                metadata=metadata.metadata,
                file_path=file_path,
                output_path=output_path
            )
            
            metadata.add_output_file(output_path)
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to process spreadsheet {file_path}: {str(e)}")
            metadata.add_error(self.name, str(e))
            return metadata 