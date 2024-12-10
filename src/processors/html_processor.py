"""HTML processing and conversion functionality."""

import base64
import re
from pathlib import Path
from typing import List, Optional, TypeAlias, Union, cast

import fitz  # PyMuPDF
import structlog
from bs4 import BeautifulSoup, NavigableString, Tag
from markdown import markdown

from src.core.exceptions import ProcessingError

logger = structlog.get_logger(__name__)

# Type aliases
HTMLContent: TypeAlias = str
MarkdownContent: TypeAlias = str
ImageData: TypeAlias = bytes
SoupTag: TypeAlias = Tag


class HTMLProcessor:
    """Processor for converting markdown to HTML and handling HTML files."""

    def __init__(
        self, temp_dir: Path, template_dir: Path, error_tolerance: bool = False
    ) -> None:
        """Initialize the HTML processor.

        Args:
            temp_dir: Directory for temporary files
            template_dir: Directory containing HTML templates
            error_tolerance: Whether to continue on errors
        """
        self.temp_dir = temp_dir
        self.template_dir = template_dir
        self.error_tolerance = error_tolerance
        self.logger = logger

        # Create temp directory
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def process_content(self, content: MarkdownContent) -> HTMLContent:
        """Process markdown content to HTML.

        Args:
            content: Markdown content to process

        Returns:
            Processed HTML content

        Raises:
            ProcessingError: If processing fails
        """
        try:
            # Convert markdown to HTML
            html_content = markdown(
                content,
                extensions=[
                    "extra",
                    "codehilite",
                    "tables",
                    "fenced_code",
                    "sane_lists",
                ],
            )

            # Wrap content in container div
            html_content = f'<div class="content">{html_content}</div>'

            return html_content

        except Exception as err:
            self.logger.error("Error processing content to HTML", exc_info=err)
            if not self.error_tolerance:
                raise ProcessingError("Failed to process content to HTML") from err
            return ""

    def _clean_text_content(self, soup: BeautifulSoup) -> None:
        """Clean up text content in BeautifulSoup object.

        Args:
            soup: BeautifulSoup object to clean
        """
        for text in soup.find_all(string=True):
            if isinstance(text, NavigableString):
                parent = text.parent
                if parent and parent.name not in ["code", "pre"]:
                    # Remove any remaining base64 content
                    if "base64," in text:
                        text.replace_with("")
                    # Clean up text encoding
                    else:
                        cleaned = self._clean_text(str(text))
                        text.replace_with(cleaned)

    def _add_styles(self, soup: BeautifulSoup) -> None:
        """Add default styles to BeautifulSoup object.

        Args:
            soup: BeautifulSoup object to add styles to
        """
        style = soup.new_tag("style")
        style.string = self._get_default_styles()

        head = soup.find("head")
        if not head:
            head = soup.new_tag("head")
            soup.insert(0, head)
        head.append(style)

    def _process_images(self, soup: BeautifulSoup) -> None:
        """Process images in BeautifulSoup object.

        Args:
            soup: BeautifulSoup object to process images in
        """
        for img in soup.find_all("img"):
            if isinstance(img, Tag):
                src = img.get("src", "")
                if src.startswith("data:"):
                    img["style"] = "max-width: 100%; height: auto;"
                    # Extract image data and save to file
                    try:
                        img_data = self._extract_base64_image(src)
                        if img_data:
                            temp_path = self.temp_dir / f"img_{hash(src)}.png"
                            temp_path.write_bytes(img_data)
                            img["src"] = str(temp_path)
                    except Exception as err:
                        self.logger.warning(f"Failed to process base64 image: {err}")
                        img.decompose()

    def _get_default_styles(self) -> str:
        """Get default CSS styles.

        Returns:
            CSS styles as string
        """
        return """
            body {
                font-family: -apple-system, system-ui, sans-serif;
                line-height: 1.6;
                font-size: 14px;
            }
            img { max-width: 100%; height: auto; }
            img[src^="data:"] { display: block; margin: 1em auto; }
            h1 {
                page-break-before: always;
                color: #2c3e50;
                font-size: 24px;
                margin-top: 2em;
                margin-bottom: 1em;
            }
            h1:first-of-type { page-break-before: avoid; }
            h2 {
                color: #34495e;
                font-size: 20px;
                margin-top: 1.5em;
            }
            h3 {
                color: #34495e;
                font-size: 16px;
                margin-top: 1.2em;
            }
            code {
                background: #f8f9fa;
                padding: 0.2em 0.4em;
                border-radius: 3px;
                font-family: 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace;
            }
            pre {
                background: #f8f9fa;
                padding: 1em;
                border-radius: 3px;
                overflow-x: auto;
                font-family: 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace;
            }
            table {
                border-collapse: collapse;
                width: 100%;
                margin: 1em 0;
                page-break-inside: avoid;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }
            th { background: #f8f9fa; }
            a { color: #3498db; text-decoration: none; }
            a:hover { text-decoration: underline; }
            hr { border: 0; border-top: 1px solid #eee; margin: 2em 0; }
            blockquote {
                border-left: 4px solid #eee;
                margin: 1em 0;
                padding-left: 1em;
                color: #666;
            }
            ul, ol {
                padding-left: 2em;
                margin: 1em 0;
            }
            li { margin: 0.5em 0; }
            p { margin: 1em 0; }
        """

    def _preprocess_markdown(self, content: str) -> str:
        """Pre-process markdown content to handle special cases.

        Args:
            content: Raw markdown content

        Returns:
            Preprocessed content
        """
        lines = []
        state = {
            "in_code_block": False,
            "in_latex_block": False,
            "current_section_level": 0,
            "conversation_mode": False,
            "last_line_empty": True,
        }

        for line in content.splitlines():
            processed_line = self._process_line(line, state)
            if processed_line is not None:
                lines.append(processed_line)

        content = "\n".join(lines)
        content = self._post_process_content(content)
        return content

    def _process_line(self, line: str, state: dict[str, bool | int]) -> Optional[str]:
        """Process a single line of markdown.

        Args:
            line: Line to process
            state: Current processing state

        Returns:
            Processed line or None if line should be skipped
        """
        # Track code blocks
        if line.strip().startswith("```"):
            state["in_code_block"] = not state["in_code_block"]
            state["last_line_empty"] = False
            return line

        # Don't process content in code blocks
        if state["in_code_block"]:
            state["last_line_empty"] = False
            return line

        # Handle LaTeX blocks
        if line.strip().startswith("\\begin{"):
            state["in_latex_block"] = True
            return None
        if line.strip().startswith("\\end{"):
            state["in_latex_block"] = False
            return None
        if state["in_latex_block"]:
            return None

        # Clean up the line
        cleaned_line = self._clean_line(line)

        # Skip empty or invalid lines
        if not cleaned_line:
            if not state["last_line_empty"]:
                state["last_line_empty"] = True
                return ""
            return None

        # Handle section markers
        if cleaned_line.startswith("\\section"):
            section_text = cleaned_line.split("{")[-1].rstrip("}")
            cleaned_line = f"# {section_text}"

        # Handle conversation markers
        if cleaned_line.startswith(
            ("YOU:", "OTHERS:", "USER:", "ASSISTANT:", "Human:", "Assistant:")
        ):
            if not state["conversation_mode"]:
                if not state["last_line_empty"]:
                    lines = ["", "## Conversation", ""]
                    state["conversation_mode"] = True
                    return "\n".join(lines + [cleaned_line])
            speaker, text = cleaned_line.split(":", 1)
            cleaned_line = f"**{speaker.title()}**: {text.strip()}"
        else:
            state["conversation_mode"] = False

        # Handle headings
        if cleaned_line.startswith("#"):
            level = len(cleaned_line.split()[0])
            if level > state["current_section_level"] + 1:
                level = state["current_section_level"] + 1
            state["current_section_level"] = level
            heading_text = " ".join(cleaned_line.split()[1:])
            cleaned_line = f"{'#' * level} {heading_text}"

            if not state["last_line_empty"]:
                return "\n" + cleaned_line

        state["last_line_empty"] = not bool(cleaned_line.strip())
        return cleaned_line

    def _post_process_content(self, content: str) -> str:
        """Post-process markdown content.

        Args:
            content: Content to post-process

        Returns:
            Post-processed content
        """
        # Clean up multiple empty lines
        content = re.sub(r"\n{3,}", "\n\n", content)

        # Fix markdown links
        content = re.sub(r"\[([^\]]+)\]\s*\(([^)]+)\)", r"[\1](\2)", content)

        # Remove any remaining LaTeX commands
        content = re.sub(r"\\[a-zA-Z]+(\{[^}]*\})*", "", content)

        return content

    def _clean_line(self, line: str) -> str:
        """Clean up a single line of text.

        Args:
            line: Line to clean

        Returns:
            Cleaned line
        """
        # Remove null bytes and control characters
        line = "".join(char for char in line if ord(char) >= 32 or char in "\n\r\t")

        # Handle base64 content
        if "base64," in line:
            if line.strip().startswith("!"):
                return line
            return ""

        # Clean up whitespace
        line = line.strip()

        # Remove HTML tags except for allowed ones
        allowed_tags = {"<br>", "<hr>", "<sup>", "<sub>", "<em>", "<strong>"}
        line = re.sub(
            r"<[^>]+>",
            lambda m: m.group(0) if m.group(0) in allowed_tags else "",
            line,
        )

        # Fix common formatting issues
        line = re.sub(r"\*\*\s+", "**", line)
        line = re.sub(r"\s+\*\*", "**", line)
        line = re.sub(r"_\s+", "_", line)
        line = re.sub(r"\s+_", "_", line)

        # Fix list markers
        line = re.sub(r"^\s*[-*+]\s+", "- ", line)
        line = re.sub(r"^\s*(\d+)\.\s+", r"\1. ", line)

        # Handle timestamps and dates
        line = re.sub(r"\d{2}:\d{2}:\d{2}", "", line)
        line = re.sub(r"\d{4}-\d{2}-\d{2}", "", line)

        # Clean up special characters
        line = line.replace("\u2029", "\n").replace("\u2028", "\n")
        line = line.replace("&nbsp;", " ")
        line = line.replace("&quot;", '"')
        line = line.replace("&amp;", "&")
        line = line.replace("&lt;", "<")
        line = line.replace("&gt;", ">")

        return line.strip()

    def _clean_text(self, text: str) -> str:
        """Clean up text content.

        Args:
            text: Text content to clean

        Returns:
            Cleaned text
        """
        # Remove null bytes and control characters
        text = "".join(char for char in text if ord(char) >= 32 or char in "\n\r\t")

        # Normalize whitespace
        text = " ".join(text.split())

        # Handle special characters
        text = text.replace("\u2029", "\n").replace("\u2028", "\n")

        return text

    def _extract_base64_image(self, data_url: str) -> Optional[ImageData]:
        """Extract image data from base64 data URL.

        Args:
            data_url: Base64 data URL

        Returns:
            Image bytes if successful, None otherwise
        """
        try:
            header, data = data_url.split(",", 1)
            image_data = base64.b64decode(data)
            return image_data
        except Exception as err:
            self.logger.warning(f"Failed to extract base64 image: {err}")
            return None

    def generate_pdf(self, html_content: HTMLContent, output_path: Path) -> None:
        """Generate PDF from HTML content using PyMuPDF.

        Args:
            html_content: HTML content to convert
            output_path: Path to save the PDF file

        Raises:
            ProcessingError: If PDF generation fails
        """
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Create temporary directories
            temp_html = self.temp_dir / "temp.html"
            temp_img_dir = self.temp_dir / "images"
            temp_img_dir.mkdir(parents=True, exist_ok=True)

            self.logger.info("Processing HTML content and extracting images...")

            # Process HTML and extract base64 images
            soup = BeautifulSoup(html_content, "html.parser")
            img_count = len(soup.find_all("img"))
            self.logger.info(f"Found {img_count} images to process")

            # Process images in chunks
            chunk_size = 5
            for i in range(0, img_count, chunk_size):
                chunk_end = min(i + chunk_size, img_count)
                self.logger.info(f"Processing images {i+1}-{chunk_end} of {img_count}")

                for img in list(soup.find_all("img"))[i:chunk_end]:
                    if isinstance(img, Tag):
                        src = img.get("src", "")
                        if src.startswith("data:"):
                            try:
                                # Extract image type and data
                                header, data = src.split(",", 1)
                                image_type = header.split(";")[0].split("/")[1]

                                # Save image to temp file
                                img_path = temp_img_dir / f"image_{i}.{image_type}"
                                img_data = base64.b64decode(data)
                                img_path.write_bytes(img_data)

                                # Update image source to file path
                                img["src"] = str(img_path)

                                # Clear the original base64 data to free memory
                                data = None
                                img_data = None

                            except Exception as err:
                                self.logger.warning(
                                    f"Failed to extract base64 image {i}: {err}"
                                )
                                # Remove failed images to prevent PDF generation issues
                                img.decompose()
                                continue

            self.logger.info("Writing temporary HTML file...")

            # Write temporary HTML file in chunks
            chunk_size = 1024 * 1024  # 1MB chunks
            html_str = str(soup)
            with temp_html.open("w", encoding="utf-8") as f:
                for i in range(0, len(html_str), chunk_size):
                    f.write(html_str[i : i + chunk_size])

            # Clear memory
            soup = None
            html_content = None
            html_str = None

            self.logger.info("Generating PDF with PyMuPDF...")

            # Create a new PDF document
            doc = fitz.open()

            # Read and parse HTML
            with temp_html.open("r", encoding="utf-8") as f:
                html_str = f.read()
                soup = BeautifulSoup(html_str, "html.parser")

            # Process content and create pages
            current_page = doc.new_page(width=595, height=842)  # A4 size
            y_position = 50

            # Process each element
            for element in soup.find_all(["h1", "h2", "h3", "p", "img"]):
                if isinstance(element, Tag):
                    if element.name == "img":
                        try:
                            # Handle images
                            src = element.get("src", "")
                            if src and Path(src).exists():
                                # Get image dimensions
                                img = fitz.Pixmap(src)

                                # Calculate scaled dimensions to fit page width
                                max_width = (
                                    495  # Page width (595) - margins (50 each side)
                                )
                                scale = min(1.0, max_width / img.width)
                                scaled_width = img.width * scale
                                scaled_height = img.height * scale

                                # Check if image needs a new page
                                if y_position + scaled_height > 800:
                                    current_page = doc.new_page(width=595, height=842)
                                    y_position = 50

                                # Calculate image rectangle
                                x0 = (595 - scaled_width) / 2  # Center horizontally
                                x1 = x0 + scaled_width
                                y1 = y_position + scaled_height

                                try:
                                    # Insert image with error handling
                                    img_rect = fitz.Rect(x0, y_position, x1, y1)
                                    current_page.insert_image(img_rect, filename=src)
                                    y_position = y1 + 20  # Add padding after image
                                except Exception as img_err:
                                    self.logger.warning(
                                        f"Failed to insert image {src}: {img_err}"
                                    )
                                    # Add placeholder text for failed image
                                    current_page.insert_text(
                                        (50, y_position), f"[Image: {Path(src).name}]"
                                    )
                                    y_position += 30

                                # Clean up
                                img = None
                        except Exception as err:
                            self.logger.warning(f"Error processing image: {err}")
                            # Add placeholder text for failed image
                            current_page.insert_text(
                                (50, y_position), "[Image processing failed]"
                            )
                            y_position += 30
                    else:
                        # Handle text elements
                        text = element.get_text().strip()
                        if text:
                            # Determine font size based on element type
                            font_size = {"h1": 16, "h2": 14, "h3": 12}.get(
                                element.name, 11
                            )

                            # Check if we need a new page
                            if y_position + font_size + 10 > 800:
                                current_page = doc.new_page(width=595, height=842)
                                y_position = 50

                            try:
                                current_page.insert_text(
                                    (50, y_position), text, fontsize=font_size
                                )
                                y_position += font_size + 10
                            except Exception as text_err:
                                self.logger.warning(
                                    f"Failed to insert text: {text_err}"
                                )
                                y_position += font_size + 10

            # Save the PDF
            doc.save(str(output_path))
            doc.close()

            # Clean up temporary files
            for file in temp_img_dir.glob("*"):
                file.unlink()
            temp_img_dir.rmdir()
            temp_html.unlink()

        except Exception as err:
            self.logger.error("Error generating PDF", exc_info=err)
            raise ProcessingError("Failed to generate PDF") from err

    def convert_to_html(self, content: str, output_path: Path) -> None:
        """Convert content to HTML and save to file.

        Args:
            content: Content to convert
            output_path: Path to save HTML file
            
        Raises:
            ProcessingError: If conversion fails
        """
        try:
            html_content = self.process_content(content)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(html_content, encoding='utf-8')
            self.logger.info(f"Saved HTML file: {output_path}")
        except Exception as err:
            self.logger.error("Failed to convert to HTML", exc_info=err)
            if not self.error_tolerance:
                raise ProcessingError(f"Failed to convert to HTML: {err}") from err
