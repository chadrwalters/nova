"""Spreadsheet handler for processing spreadsheet files."""

import logging
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any
from io import StringIO

import pandas as pd

from nova.context_processor.config.manager import ConfigManager
from nova.context_processor.core.metadata.models.types import SpreadsheetMetadata
from nova.context_processor.handlers.base import BaseHandler
from nova.context_processor.utils.file_utils import calculate_file_hash

logger = logging.getLogger(__name__)


class SpreadsheetHandler(BaseHandler):
    """Handler for spreadsheet files."""

    def __init__(self, config: ConfigManager):
        """Initialize handler.

        Args:
            config: Configuration manager
        """
        super().__init__(config)
        self.supported_extensions = {".xlsx", ".xls", ".csv"}

    async def _extract_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Extract information from a spreadsheet file.

        Args:
            file_path: Path to file

        Returns:
            Optional[Dict[str, Any]]: Spreadsheet information if successful, None if failed
        """
        try:
            extension = file_path.suffix.lower()
            info = {
                "sheet_count": 0,
                "total_rows": 0,
                "total_columns": 0,
                "sheets": {},
                "has_formulas": False,
                "has_macros": False,
            }

            if extension == ".csv":
                # Try different encodings
                encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
                df = None
                
                for encoding in encodings:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                        
                if df is None:
                    raise ValueError(f"Could not decode CSV file with any of the encodings: {encodings}")
                    
                info["sheet_count"] = 1
                info["total_rows"] = len(df)
                info["total_columns"] = len(df.columns)
                info["sheets"] = {
                    "Sheet1": {
                        "rows": len(df),
                        "columns": len(df.columns),
                    }
                }
            else:
                # Read Excel file
                excel = pd.ExcelFile(file_path)
                info["sheet_count"] = len(excel.sheet_names)
                info["total_rows"] = 0
                info["total_columns"] = 0
                info["sheets"] = {}

                # Process each sheet
                for sheet_name in excel.sheet_names:
                    df = pd.read_excel(excel, sheet_name)
                    info["total_rows"] += len(df)
                    info["total_columns"] = max(info["total_columns"], len(df.columns))
                    info["sheets"][sheet_name] = {
                        "rows": len(df),
                        "columns": len(df.columns),
                    }

            return info

        except Exception as e:
            logger.error(f"Failed to extract spreadsheet information: {str(e)}")
            return None

    async def _process_file(self, file_path: Path, metadata: SpreadsheetMetadata) -> bool:
        """Process a spreadsheet file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether processing was successful
        """
        try:
            # Extract spreadsheet information
            info = await self._extract_info(file_path)
            if not info:
                return False

            # Update metadata
            metadata.sheet_count = info["sheet_count"]
            metadata.total_rows = info["total_rows"]
            metadata.total_columns = info["total_columns"]
            metadata.has_formulas = info["has_formulas"]
            metadata.has_macros = info["has_macros"]

            return True

        except Exception as e:
            logger.error(f"Failed to process spreadsheet {file_path}: {e}")
            return False

    async def _parse_file(self, file_path: Path, metadata: SpreadsheetMetadata) -> bool:
        """Parse a spreadsheet file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether parsing was successful
        """
        try:
            # Extract spreadsheet information
            info = await self._extract_info(file_path)
            if not info:
                return False

            # Update metadata
            metadata.sheet_count = info["sheet_count"]
            metadata.total_rows = info["total_rows"]
            metadata.total_columns = info["total_columns"]
            metadata.has_formulas = info["has_formulas"]
            metadata.has_macros = info["has_macros"]

            return True

        except Exception as e:
            logger.error(f"Failed to parse spreadsheet {file_path}: {e}")
            return False

    async def _disassemble_file(self, file_path: Path, metadata: SpreadsheetMetadata) -> bool:
        """Disassemble a spreadsheet file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether disassembly was successful
        """
        try:
            # For now, just copy the file
            metadata.file_size = file_path.stat().st_size
            metadata.file_hash = calculate_file_hash(file_path)

            return True

        except Exception as e:
            logger.error(f"Failed to disassemble spreadsheet {file_path}: {e}")
            return False

    async def _split_file(self, file_path: Path, metadata: SpreadsheetMetadata) -> bool:
        """Split a spreadsheet file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether splitting was successful
        """
        try:
            # For now, just copy the file
            metadata.file_size = file_path.stat().st_size
            metadata.file_hash = calculate_file_hash(file_path)

            return True

        except Exception as e:
            logger.error(f"Failed to split spreadsheet {file_path}: {e}")
            return False
