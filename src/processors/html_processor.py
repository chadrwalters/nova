import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import markdown
import structlog
from bs4 import BeautifulSoup
from markdown.blockprocessors import ListIndentProcessor
from markdown.extensions import Extension

from src.core.config import ProcessingConfig
from src.core.exceptions import ConsolidationError, ConversionError
from src.core.template_manager import TemplateManager

logger = structlog.get_logger(__name__)

class CustomListExtension(Extension):
    """Custom extension for better list handling."""
    def extendMarkdown(self, md):
        # Replace the default list processor with our custom one
        md.parser.blockprocessors.register(
            CustomListProcessor(md.parser),
            'list',
            175  # Priority (higher than default list processor)
        )

class CustomListProcessor(ListIndentProcessor):
    """Custom list processor that handles nested lists better."""
    def __init__(self, parser):
        super().__init__(parser)
        self.INDENT_RE = re.compile(r'^[ ]*[\*\-\+]\s+')

    def get_level(self, parent, block):
        """Get the list level."""
        # Simply use indentation to determine level
        m = self.INDENT_RE.match(block)
        if m:
            indent = len(m.group(0))
            return max(0, (indent - 2) // 2)
        return 0

class HTMLProcessor:
    """Processes HTML documents."""

    def __init__(self,
                 media_dir: Path,
                 debug_dir: Optional[Path] = None,
                 error_tolerance: str = 'lenient',
                 template_dir: Optional[Path] = None):
        """Initialize the processor."""
        self.media_dir = media_dir
        self.debug_dir = debug_dir
        self.error_tolerance = error_tolerance
        self.logger = structlog.get_logger(__name__)

    def convert_to_html(self, content: str, source_path: Path, output_dir: Path) -> Path:
        """Convert markdown content to HTML."""
        try:
            # Normalize content
            content = self._normalize_content(content)

            # Process attachments
            content = self._process_attachments(content, source_path)

            # Convert markdown to HTML
            html = markdown.markdown(
                content,
                extensions=[
                    'extra',
                    'codehilite',
                    'tables',
                    'toc',
                    'sane_lists',
                    'nl2br',
                    'smarty',
                    'meta',
                    'fenced_code',
                    'attr_list',
                    'def_list',
                    'footnotes',
                    'md_in_html'
                ],
                output_format='html5'
            )

            # Post-process HTML
            soup = BeautifulSoup(html, 'html.parser')

            # Apply styling classes to paragraphs
            for element in soup.find_all('p'):
                classes = element.get('class', [])
                if not isinstance(classes, list):
                    classes = [classes] if classes else []
                classes.append('content-paragraph')
                element['class'] = classes

            # Apply styling classes to headers
            for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                for element in soup.find_all(tag):
                    classes = element.get('class', [])
                    if not isinstance(classes, list):
                        classes = [classes] if classes else []
                    classes.append('section-header')
                    element['class'] = classes

            # Apply styling classes to strikethrough
            for element in soup.find_all('del'):
                classes = element.get('class', [])
                if not isinstance(classes, list):
                    classes = [classes] if classes else []
                classes.append('strikethrough')
                element['class'] = classes

            # Handle lists
            for ul in soup.find_all('ul'):
                classes = ul.get('class', [])
                if not isinstance(classes, list):
                    classes = [classes] if classes else []
                classes.append('content-list')
                ul['class'] = classes

                for li in ul.find_all('li', recursive=False):
                    li_classes = li.get('class', [])
                    if not isinstance(li_classes, list):
                        li_classes = [li_classes] if li_classes else []
                    li_classes.append('list-item')
                    li['class'] = li_classes

                    nested_ul = li.find('ul')
                    if nested_ul:
                        nested_classes = nested_ul.get('class', [])
                        if not isinstance(nested_classes, list):
                            nested_classes = [nested_classes] if nested_classes else []
                        nested_classes.append('nested-list')
                        nested_ul['class'] = nested_classes

                        for nested_li in nested_ul.find_all('li', recursive=False):
                            nested_li_classes = nested_li.get('class', [])
                            if not isinstance(nested_li_classes, list):
                                nested_li_classes = [nested_li_classes] if nested_li_classes else []
                            nested_li_classes.append('nested-item')
                            nested_li['class'] = nested_li_classes

            # Handle images and attachments
            for img in soup.find_all('img'):
                img_classes = img.get('class', [])
                if not isinstance(img_classes, list):
                    img_classes = [img_classes] if img_classes else []
                img_classes.append('content-image')
                img['class'] = img_classes

                # Add alt text if missing
                if not img.get('alt'):
                    img['alt'] = 'Image'

                # Move base64 images to media directory
                src = img.get('src', '')
                if src.startswith('data:image/'):
                    import base64
                    import hashlib

                    # Extract image data and format
                    format_match = re.match(r'data:image/([^;]+);base64,', src)
                    if format_match:
                        img_format = format_match.group(1)
                        img_data = src.split(',', 1)[1]

                        try:
                            # Create a hash of the image data for the filename
                            img_hash = hashlib.md5(img_data.encode()).hexdigest()
                            img_filename = f"{img_hash}.{img_format}"

                            # Save image to media directory
                            media_dir = self.debug_dir / "media" if self.debug_dir else Path("media")
                            media_dir.mkdir(parents=True, exist_ok=True)
                            img_path = media_dir / img_filename

                            if not img_path.exists():
                                img_bytes = base64.b64decode(img_data)
                                img_path.write_bytes(img_bytes)
                                self.logger.info(f"Saved base64 image to {img_path}")

                            # Update image source
                            img['src'] = f"../media/{img_filename}"
                        except Exception as e:
                            self.logger.error(f"Failed to save base64 image: {str(e)}")

            # Handle attachment links
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if '../attachments/' in href:
                    link_classes = link.get('class', [])
                    if not isinstance(link_classes, list):
                        link_classes = [link_classes] if link_classes else []
                    link_classes.append('attachment-link')
                    link['class'] = link_classes
                elif href.startswith(('http://', 'https://')):
                    link_classes = link.get('class', [])
                    if not isinstance(link_classes, list):
                        link_classes = [link_classes] if link_classes else []
                    link_classes.append('external-link')
                    link['class'] = link_classes
                    # Add target="_blank" for external links
                    link['target'] = '_blank'
                    link['rel'] = 'noopener noreferrer'

            # Create basic HTML template (with proper indentation)
            template_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 1in;
            color: black;
            background: white;
        }}
        h1 {{ margin-bottom: 1em; }}
        p {{ margin: 0.5em 0; }}
        .metadata {{
            margin: 1em 0;
            padding: 1em;
            background: #f5f5f5;
            border: 1px solid #ddd;
        }}
        .content {{
            margin-top: 2em;
            padding: 1em;
            background: white;
            border: 1px solid #eee;
        }}
        a {{
            color: #333;
            text-decoration: none;
            pointer-events: none;
        }}
        img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 1em auto;
        }}
        @media print {{
            body {{
                margin: 0;
                padding: 1in;
            }}
            .metadata {{
                page-break-inside: avoid;
            }}
            a {{
                text-decoration: none;
                color: black;
            }}
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="metadata">
        <p><strong>Source:</strong> {source_file}</p>
        <p><strong>Last Updated:</strong> {last_updated}</p>
    </div>
    <div class="content">
        {content}
    </div>
</body>
</html>"""

            # Process the soup to handle links and images
            media_dir = Path(output_dir) / "media"
            media_dir.mkdir(parents=True, exist_ok=True)

            for img in soup.find_all('img'):
                if img.get('src'):
                    src_path = Path(img['src'])
                    if src_path.exists():
                        # Copy image to media directory
                        target_path = media_dir / src_path.name
                        shutil.copy2(src_path, target_path)
                        img['src'] = str(target_path.resolve())
                    else:
                        # Remove broken image
                        img.decompose()

            for link in soup.find_all('a'):
                if link.get('href'):
                    # Convert links to text to avoid external dependencies
                    link.replace_with(link.text)

            # Create final HTML
            final_html = template_html.format(
                title=source_path.stem,
                content=str(soup),
                last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                source_file=source_path.name
            )

            # Fix about:blank protocol and other problematic URLs
            final_html = final_html.replace('about:blank', '#')
            final_html = re.sub(r'href="[^"]*"', 'href="#"', final_html)

            # Save individual file
            output_file = output_dir / f"{source_path.stem}.html"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(final_html)
            self.logger.info(f"Generated individual HTML file: {output_file}")

            return output_file

        except Exception as e:
            if not isinstance(e, ConversionError):
                raise ConversionError(f"HTML conversion failed for {source_path.name}: {str(e)}")
            raise

    def _normalize_content(self, content: str) -> str:
        """Normalize content for HTML conversion."""
        # Fix list formatting
        lines = content.split('\n')
        normalized_lines = []
        in_list = False
        list_indent = 0

        for i, line in enumerate(lines):
            stripped = line.lstrip()

            # Check if line is a list item
            list_match = re.match(r'^(\s*)[\*\-\+]\s', line)

            if list_match:
                # Calculate indentation level
                current_indent = len(list_match.group(1))

                if not in_list:
                    # Start new list - add blank line before if needed
                    if normalized_lines and normalized_lines[-1].strip():
                        normalized_lines.append('')
                    list_indent = current_indent
                    in_list = True

                # Normalize list marker and spacing
                indent = ' ' * current_indent
                normalized_lines.append(f"{indent}* {stripped[2:].lstrip()}")
            else:
                if in_list and stripped:
                    # End list - add blank line after if needed
                    if normalized_lines[-1].strip():
                        normalized_lines.append('')
                    in_list = False
                normalized_lines.append(line)

        content = '\n'.join(normalized_lines)

        # Fix common markdown issues
        content = re.sub(r'\*\s+([^*\n]+)\*', '*\\1*', content)  # Fix emphasis
        content = re.sub(r'~\s+([^~\n]+)~', '~\\1~', content)    # Fix strikethrough
        content = re.sub(r'`\s+([^`\n]+)`', '`\\1`', content)    # Fix inline code

        # Fix base64 images that might be split across lines
        content = re.sub(
            r'!\[([^\]]*)\]\(data:image/([^;]+);base64,\s*([^\)]+)\)',
            lambda m: f'![{m.group(1)}](data:image/{m.group(2)};base64,{m.group(3).replace(" ", "").replace("\n", "")})',
            content
        )

        return content

    def _process_attachments(self, content: str, source_path: Path) -> str:
        """Process attachments in the markdown content."""
        # Create attachments directory
        attachments_dir = self.debug_dir / "attachments" if self.debug_dir else Path("attachments")
        attachments_dir.mkdir(parents=True, exist_ok=True)

        def process_attachment(match):
            link_text = match.group(1)
            file_path = match.group(2)
            embed_info = match.group(3) if match.group(3) else ""

            # Check if it's an external URL
            if file_path.startswith(('http://', 'https://')):
                # Convert external URLs to text references
                domain = file_path.split('/')[2]
                return f'<span class="external-reference">{link_text} ({domain})</span>{embed_info}'

            try:
                # Get the source file directory
                source_dir = source_path.parent.resolve()

                # Handle URL-encoded paths and clean up path
                from urllib.parse import unquote
                file_path = unquote(file_path).strip()

                # Handle both absolute and relative paths
                full_source_path = Path(file_path)
                if not full_source_path.is_absolute():
                    full_source_path = (source_dir / file_path).resolve()

                # Create target path preserving directory structure
                rel_path = full_source_path.relative_to(source_dir) if source_dir in full_source_path.parents else full_source_path.name
                target_path = attachments_dir / rel_path

                # Create target directory
                target_path.parent.mkdir(parents=True, exist_ok=True)

                # Copy file if it exists
                if full_source_path.exists():
                    import shutil
                    shutil.copy2(full_source_path, target_path)
                    self.logger.debug(f"Copied attachment: {full_source_path} -> {target_path}")
                    # Update link to point to attachments directory
                    return f'<a href="../attachments/{rel_path}" class="attachment-link">{link_text}</a>{embed_info}'
                else:
                    # Only log debug for local files
                    self.logger.debug(f"Local attachment not found: {full_source_path}")
                    # Keep original text without link
                    return f'<span class="missing-attachment">{link_text}</span>{embed_info}'

            except Exception as e:
                self.logger.error(f"Failed to process attachment {file_path}: {str(e)}")
                # Keep original text without link
                return f'<span class="error-attachment">{link_text}</span>{embed_info}'

        # Process markdown links with optional embed comments
        content = re.sub(
            r'\[([^\]]+)\]\(([^)]+)\)(?:<!--\s*({[^}]+})\s*-->)?',
            process_attachment,
            content
        )

        return content

    def _fix_malformed_images(self, content: str) -> str:
        """Fix malformed image tags in markdown content."""
        try:
            # Fix incomplete image tags at start of file
            if content.startswith('!['):
                content = '\n' + content

            # Fix base64 image tags that are split across lines
            content = re.sub(
                r'!\[([^\]]*)\]\(data:image/([^;]+);base64,\s*\n\s*([^\)]+)\)',
                r'![\1](data:image/\2;base64,\3)',
                content
            )

            # Fix image tags with newlines between parts
            content = re.sub(
                r'!\[([^\]]*)\]\s*\n\s*\(([^\)]+)\)',
                r'![\1](\2)',
                content
            )

            # Fix relative paths to use _media directory
            content = re.sub(
                r'!\[([^\]]*)\]\((?!(?:https?://|data:))([^/][^\)]+)\)',
                r'![\1](_media/\2)',
                content
            )

            return content.strip()

        except Exception as e:
            logger.error("Failed to fix malformed images",
                        error=str(e),
                        exc_info=True)
            return content  # Return original content on error

    def _fix_list_formatting(self, content: str) -> str:
        """Fix list formatting in markdown content."""
        # Split content into lines
        lines = content.split('\n')
        fixed_lines = []
        in_list = False
        list_indent = 0
        list_buffer = []

        for i, line in enumerate(lines):
            stripped = line.lstrip()

            # Check if line is a list item
            list_match = re.match(r'^(\s*)[\*\-\+]\s', line)

            if list_match:
                # Calculate indentation level
                current_indent = len(list_match.group(1))

                if not in_list:
                    # Start new list - add blank line before if needed
                    if fixed_lines and fixed_lines[-1].strip():
                        fixed_lines.append('')
                    list_indent = current_indent
                    in_list = True

                # Add to list buffer with proper indentation
                indent_level = (current_indent - list_indent) // 2
                list_buffer.append((indent_level, stripped[2:].lstrip()))
            else:
                if in_list:
                    # Process list buffer
                    if list_buffer:
                        # Add list items with proper formatting
                        for level, text in list_buffer:
                            fixed_lines.append('  ' * level + '* ' + text)
                        list_buffer = []

                    # Add blank line after list if needed
                    if stripped:
                        fixed_lines.append('')
                    in_list = False

                # Add non-list line
                fixed_lines.append(line)

        # Process any remaining list buffer
        if list_buffer:
            for level, text in list_buffer:
                fixed_lines.append('  ' * level + '* ' + text)

        # Join lines and fix any remaining formatting issues
        content = '\n'.join(fixed_lines)

        # Fix common list formatting issues
        content = re.sub(r'(?m)^(\s*)\* \s+', r'\1* ', content)  # Remove extra spaces after list marker
        content = re.sub(r'(?m)^(\s*)[\-\+]\s', r'\1* ', content)  # Standardize list markers to *
        content = re.sub(r'\n{3,}', '\n\n', content)  # Normalize multiple blank lines

        # Fix list items that are wrapped in paragraphs
        content = re.sub(r'(?m)^(\s*)\* ([^\n]+)(?:\n(?!\s*[\*\-\+]\s)[^\n]+)*', r'\1* \2', content)

        # Fix list items that are not properly indented
        content = re.sub(r'(?m)^(\s*)\* ([^\n]+)(?:\n(?!\s*[\*\-\+]\s)[^\n]+)*', r'\1* \2', content)

        # Fix list items that are not properly spaced
        content = re.sub(r'(?m)^(\s*)\* ([^\n]+)(?:\n(?!\s*[\*\-\+]\s)[^\n]+)*', r'\1* \2', content)

        # Fix list items that are not properly formatted
        content = re.sub(r'(?m)^(\s*)\* ([^\n]+)(?:\n(?!\s*[\*\-\+]\s)[^\n]+)*', r'\1* \2', content)

        return content

    def consolidate_html_files(self, html_files: List[Path], output_file: Path) -> None:
        """Consolidate multiple HTML files into one."""
        try:
            combined_content = []

            # Process each HTML file
            for html_file in html_files:
                try:
                    with html_file.open('r', encoding='utf-8') as f:
                        soup = BeautifulSoup(f.read(), 'html.parser')

                    # Extract body content
                    body_content = soup.find('body')
                    if not body_content:
                        continue

                    # Update image paths
                    for img in body_content.find_all('img'):
                        if 'src' in img.attrs:
                            img['src'] = img['src'].replace('../_media', '_media')

                    combined_content.append(str(body_content))
                except Exception as e:
                    raise ConsolidationError(
                        f"Failed to process HTML file {html_file.name}: {e}"
                    )

            # Generate combined HTML
            try:
                template = r'''<!DOCTYPE html>
<html>
<head>
    <title>Combined Document</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 1rem; }}
        .content-paragraph {{ margin-bottom: 1rem; }}
        .section-header {{ margin-top: 2rem; margin-bottom: 1rem; }}
        .content-list {{ margin-bottom: 1rem; list-style-type: disc; }}
        .list-item {{ margin: 0.5rem 0; }}
        .nested-list {{ margin-top: 0.5rem; margin-left: 2rem; list-style-type: circle; }}
        .nested-item {{ margin: 0.25rem 0; }}
        .strikethrough {{ text-decoration: line-through; }}
        .content-image {{ max-width: 100%; height: auto; margin: 1rem 0; }}
        .attachment-link {{ display: inline-block; padding: 0.5rem 1rem; margin: 0.5rem 0; background-color: #f5f5f5; border-radius: 4px; text-decoration: none; color: #333; }}
    </style>
</head>
<body>
{content}
</body>
</html>'''

                # Write output file
                final_html = template.format(content="\n".join(combined_content))
                output_file.write_text(final_html, encoding='utf-8')
                self.logger.info(f"Generated consolidated HTML: {output_file}")

            except Exception as e:
                raise ConsolidationError(f"Failed to generate combined HTML: {e}")

        except Exception as e:
            raise ConsolidationError(f"Failed to consolidate HTML files: {e}")
