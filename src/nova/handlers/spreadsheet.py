"""Spreadsheet file handler."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Union

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
            
            # Write markdown using MarkdownWriter and get the content
            markdown_content = self.markdown_writer.write_document(
                title=metadata.title,
                content=content,
                metadata=metadata.metadata,
                file_path=file_path,
                output_path=output_path
            )
            
            # Create parent directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write the markdown content to the output file
            output_path.write_text(markdown_content, encoding='utf-8')
            
            metadata.add_output_file(output_path)
            
            # Get relative path from input directory
            relative_path = Path(os.path.relpath(file_path, self.config.input_dir))
            
            # Save metadata using relative path
            self._save_metadata(file_path, relative_path, metadata)
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to process spreadsheet {file_path}: {str(e)}")
            metadata.add_error(self.name, str(e))
            return metadata 