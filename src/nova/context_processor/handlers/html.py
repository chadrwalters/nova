"""HTML handler for Nova document processor."""

import logging
from pathlib import Path

from bs4 import BeautifulSoup

from nova.context_processor.core.metadata.models.types import HTMLMetadata
from nova.context_processor.handlers.base import BaseHandler
from nova.context_processor.utils.file_utils import calculate_file_hash

logger = logging.getLogger(__name__)


class HTMLHandler(BaseHandler):
    """Handler for HTML files."""

    def __init__(self, config):
        """Initialize handler.

        Args:
            config: Nova configuration
        """
        super().__init__(config)
        self.supported_extensions = {
            ".html",
            ".htm",
        }

    async def _process_file(self, file_path: Path, metadata: HTMLMetadata) -> bool:
        """Process an HTML file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether processing was successful
        """
        try:
            # Read HTML content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse HTML
            soup = BeautifulSoup(content, "html.parser")

            # Extract metadata
            metadata.title = soup.title.string if soup.title else file_path.stem
            metadata.content = soup.get_text()
            metadata.file_size = file_path.stat().st_size
            metadata.file_hash = calculate_file_hash(file_path)

            # Extract links
            metadata.links = {str(a.get("href")) for a in soup.find_all("a") if a.get("href")}

            # Extract images
            metadata.images = {str(img.get("src")) for img in soup.find_all("img") if img.get("src")}

            # Extract scripts
            metadata.scripts = {str(script.get("src")) for script in soup.find_all("script") if script.get("src")}

            # Extract styles
            metadata.styles = {str(link.get("href")) for link in soup.find_all("link", rel="stylesheet") if link.get("href")}

            # Extract charset
            charset_meta = soup.find("meta", charset=True)
            if charset_meta:
                metadata.charset = charset_meta.get("charset")
            else:
                content_meta = soup.find("meta", {"http-equiv": "Content-Type"})
                if content_meta:
                    content = content_meta.get("content", "")
                    if "charset=" in content:
                        metadata.charset = content.split("charset=")[-1]

            return True

        except Exception as e:
            logger.error(f"Failed to process HTML file {file_path}: {e}")
            return False

    async def _parse_file(self, file_path: Path, metadata: HTMLMetadata) -> bool:
        """Parse an HTML file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether parsing was successful
        """
        try:
            # Read HTML content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse HTML
            soup = BeautifulSoup(content, "html.parser")

            # Extract metadata
            metadata.title = soup.title.string if soup.title else file_path.stem
            metadata.content = soup.get_text()
            metadata.file_size = file_path.stat().st_size
            metadata.file_hash = calculate_file_hash(file_path)

            # Extract links
            metadata.links = {str(a.get("href")) for a in soup.find_all("a") if a.get("href")}

            # Extract images
            metadata.images = {str(img.get("src")) for img in soup.find_all("img") if img.get("src")}

            # Extract scripts
            metadata.scripts = {str(script.get("src")) for script in soup.find_all("script") if script.get("src")}

            # Extract styles
            metadata.styles = {str(link.get("href")) for link in soup.find_all("link", rel="stylesheet") if link.get("href")}

            # Extract charset
            charset_meta = soup.find("meta", charset=True)
            if charset_meta:
                metadata.charset = charset_meta.get("charset")
            else:
                content_meta = soup.find("meta", {"http-equiv": "Content-Type"})
                if content_meta:
                    content = content_meta.get("content", "")
                    if "charset=" in content:
                        metadata.charset = content.split("charset=")[-1]

            return True

        except Exception as e:
            logger.error(f"Failed to parse HTML file {file_path}: {e}")
            return False

    async def _disassemble_file(self, file_path: Path, metadata: HTMLMetadata) -> bool:
        """Disassemble an HTML file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether disassembly was successful
        """
        try:
            # For now, just copy the file
            metadata.title = file_path.stem
            metadata.file_size = file_path.stat().st_size
            metadata.file_hash = calculate_file_hash(file_path)

            return True

        except Exception as e:
            logger.error(f"Failed to disassemble HTML file {file_path}: {e}")
            return False

    async def _split_file(self, file_path: Path, metadata: HTMLMetadata) -> bool:
        """Split an HTML file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether splitting was successful
        """
        try:
            # For now, just copy the file
            metadata.title = file_path.stem
            metadata.file_size = file_path.stat().st_size
            metadata.file_hash = calculate_file_hash(file_path)

            return True

        except Exception as e:
            logger.error(f"Failed to split HTML file {file_path}: {e}")
            return False
