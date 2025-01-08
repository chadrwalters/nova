"""Text file handler."""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

from nova.context_processor.config.manager import ConfigManager
from nova.context_processor.core.metadata.models.types import TextMetadata
from nova.context_processor.handlers.base import BaseHandler
from nova.context_processor.utils.file_utils import calculate_file_hash

logger = logging.getLogger(__name__)


class TextHandler(BaseHandler):
    """Handler for text files."""

    def __init__(self, config: ConfigManager) -> None:
        """Initialize text handler.

        Args:
            config: Configuration manager
        """
        super().__init__(config)
        self.supported_extensions = {".txt", ".log", ".env", ".ini", ".cfg", ".conf"}

    async def _extract_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Extract information from a text file.

        Args:
            file_path: Path to file

        Returns:
            Optional[Dict[str, Any]]: Text information if successful, None if failed
        """
        try:
            info = {
                "line_count": 0,
                "word_count": 0,
                "char_count": 0,
                "encoding": None,
                "is_binary": False,
            }

            # Try different encodings
            encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
            content = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                        info["encoding"] = encoding
                    break
                except UnicodeDecodeError:
                    continue
                    
            if content is None:
                info["is_binary"] = True
                return info

            # Count lines, words, and characters
            info["line_count"] = len(content.splitlines())
            info["word_count"] = len(content.split())
            info["char_count"] = len(content)

            return info

        except Exception as e:
            logger.error(f"Failed to extract text information: {str(e)}")
            return None

    async def _process_file(self, file_path: Path, metadata: TextMetadata) -> bool:
        """Process a text file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether processing was successful
        """
        try:
            # Extract text information
            info = await self._extract_info(file_path)
            if not info:
                return False

            # Update metadata
            metadata.line_count = info["line_count"]
            metadata.word_count = info["word_count"]
            metadata.char_count = info["char_count"]
            metadata.encoding = info["encoding"]
            metadata.is_binary = info["is_binary"]

            return True

        except Exception as e:
            logger.error(f"Failed to process text {file_path}: {e}")
            return False

    async def _parse_file(self, file_path: Path, metadata: TextMetadata) -> bool:
        """Parse a text file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether parsing was successful
        """
        try:
            # Extract text information
            info = await self._extract_info(file_path)
            if not info:
                return False

            # Update metadata
            metadata.line_count = info["line_count"]
            metadata.word_count = info["word_count"]
            metadata.char_count = info["char_count"]
            metadata.encoding = info["encoding"]
            metadata.is_binary = info["is_binary"]

            return True

        except Exception as e:
            logger.error(f"Failed to parse text {file_path}: {e}")
            return False

    async def _disassemble_file(self, file_path: Path, metadata: TextMetadata) -> bool:
        """Disassemble a text file.

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
            logger.error(f"Failed to disassemble text {file_path}: {e}")
            return False

    async def _split_file(self, file_path: Path, metadata: TextMetadata) -> bool:
        """Split a text file.

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
            logger.error(f"Failed to split text {file_path}: {e}")
            return False
