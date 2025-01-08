"""Markdown processing utilities."""

import logging
import re
from pathlib import Path
from typing import Optional, List, Tuple

import markdown
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class MarkdownWriter:
    """Markdown writer and processor."""

    def __init__(self):
        """Initialize markdown writer."""
        self.md = markdown.Markdown(extensions=['extra', 'meta'])

    def convert(self, content: str) -> str:
        """Convert markdown content.

        Args:
            content: Raw markdown content

        Returns:
            Processed markdown content
        """
        try:
            # Convert to HTML
            html = self.md.convert(content)
            
            # Parse HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # Clean up formatting
            processed_content = []
            
            # Process headings
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                level = int(heading.name[1])
                text = heading.get_text().strip()
                processed_content.append(f"{'#' * level} {text}\n")
            
            # Process paragraphs
            for p in soup.find_all('p'):
                text = p.get_text().strip()
                if text:
                    processed_content.append(f"{text}\n\n")
            
            # Process lists
            for ul in soup.find_all(['ul', 'ol']):
                is_ordered = ul.name == 'ol'
                for i, li in enumerate(ul.find_all('li', recursive=False), 1):
                    text = li.get_text().strip()
                    if is_ordered:
                        processed_content.append(f"{i}. {text}\n")
                    else:
                        processed_content.append(f"* {text}\n")
                processed_content.append("\n")
            
            # Process code blocks
            for pre in soup.find_all('pre'):
                code = pre.get_text().strip()
                processed_content.append(f"```\n{code}\n```\n\n")
            
            # Process tables
            for table in soup.find_all('table'):
                rows = []
                # Headers
                headers = []
                for th in table.find_all('th'):
                    headers.append(th.get_text().strip())
                if headers:
                    rows.append("| " + " | ".join(headers) + " |")
                    rows.append("| " + " | ".join(["---"] * len(headers)) + " |")
                
                # Data rows
                for tr in table.find_all('tr'):
                    cells = []
                    for td in tr.find_all('td'):
                        cells.append(td.get_text().strip())
                    if cells:
                        rows.append("| " + " | ".join(cells) + " |")
                
                processed_content.extend(rows)
                processed_content.append("\n")
            
            # Join all parts
            result = "\n".join(processed_content)
            
            # Clean up extra newlines
            result = re.sub(r'\n{3,}', '\n\n', result)
            
            return result.strip()

        except Exception as e:
            logger.error(f"Failed to process markdown: {str(e)}")
            return content  # Return original content on error

    def extract_metadata(self, content: str) -> Tuple[dict, str]:
        """Extract metadata from markdown content.

        Args:
            content: Markdown content

        Returns:
            Tuple of (metadata dict, content without metadata)
        """
        try:
            # Convert content
            self.md.convert(content)
            
            # Get metadata
            metadata = self.md.Meta.copy() if hasattr(self.md, 'Meta') else {}
            
            # Clean up metadata values
            for key, value in metadata.items():
                if isinstance(value, list) and len(value) == 1:
                    metadata[key] = value[0]
            
            # Remove metadata block from content
            content_lines = content.split('\n')
            while content_lines and not content_lines[0].strip():
                content_lines.pop(0)
            
            # Find end of metadata block
            for i, line in enumerate(content_lines):
                if line.strip() and not line.startswith('---'):
                    content = '\n'.join(content_lines[i:])
                    break
            
            return metadata, content

        except Exception as e:
            logger.error(f"Failed to extract metadata: {str(e)}")
            return {}, content  # Return empty metadata and original content on error