"""Spreadsheet file handler."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Union
import mimetypes

import pandas as pd

from ..models.document import DocumentMetadata
from .base import BaseHandler, ProcessingStatus, ProcessingResult
from ..config.manager import ConfigManager
from ..core.markdown import MarkdownWriter


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
    
    def _extract_excel_text(self, file_path: Path) -> str:
        """Extract text from Excel file.
        
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
            
    def _extract_csv_text(self, file_path: Path) -> str:
        """Extract text from CSV file.
        
        Args:
            file_path: Path to CSV file.
            
        Returns:
            Markdown table representation of CSV file.
        """
        encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252', 'iso-8859-1']
        last_error = None
        
        for encoding in encodings:
            try:
                # Read CSV file with specific encoding
                df = pd.read_csv(file_path, encoding=encoding)
                
                # Convert to markdown table
                return df.to_markdown(index=False)
                
            except UnicodeDecodeError as e:
                last_error = e
                continue
            except Exception as e:
                return f"Error converting CSV to markdown: {str(e)}"
        
        return f"Error converting CSV to markdown: Failed to decode with encodings {encodings}. Last error: {str(last_error)}"
        
    async def process_file_impl(
        self,
        file_path: Path,
        output_path: Path,
        metadata: DocumentMetadata,
    ) -> Optional[DocumentMetadata]:
        """Process a spreadsheet file.
        
        Args:
            file_path: Path to spreadsheet file.
            output_path: Path to write output.
            metadata: Document metadata.
            
        Returns:
            Document metadata.
        """
        try:
            # Extract content based on file type
            if file_path.suffix.lower() in ['.xlsx', '.xls']:
                content = self._extract_excel_text(file_path)
            elif file_path.suffix.lower() == '.csv':
                content = self._extract_csv_text(file_path)
            else:
                raise ValueError(f"Unsupported spreadsheet type: {file_path.suffix}")
            
            # Update metadata
            metadata.title = file_path.stem
            metadata.processed = True
            metadata.metadata.update({
                'file_type': mimetypes.guess_type(file_path)[0] or f"application/{file_path.suffix.lstrip('.')}",
                'file_size': os.path.getsize(file_path)
            })
            
            # Create spreadsheet marker
            sheet_type = 'EXCEL' if file_path.suffix.lower() in ['.xlsx', '.xls'] else 'CSV'
            sheet_marker = f"[ATTACH:{sheet_type}:{file_path.stem}]"
            
            # Write markdown using MarkdownWriter
            markdown_content = self.markdown_writer.write_document(
                title=metadata.title,
                content=f"{sheet_marker}\n\n{content}",
                metadata=metadata.metadata,
                file_path=file_path,
                output_path=output_path
            )
            
            # Write the file
            self._safe_write_file(output_path, markdown_content)
            
            metadata.add_output_file(output_path)
            return metadata
            
        except Exception as e:
            error_msg = f"Failed to process spreadsheet {file_path}: {str(e)}"
            self.logger.error(error_msg)
            if metadata:
                metadata.add_error(self.name, error_msg)
                metadata.processed = False
            return metadata 