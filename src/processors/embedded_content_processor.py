import hashlib
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Protocol, TypedDict, Union

import structlog

from .attachment_processor import AttachmentProcessor, ProcessedAttachment

logger = structlog.get_logger(__name__)


class EmbeddedContentMetadata(TypedDict):
    content_type: str  # diagram, code, math, etc.
    language: str  # mermaid, plantuml, latex, python, etc.
    line_number: int
    context: str
    hash: str
    created: datetime
    is_preview: bool
    settings: Dict


@dataclass
class ProcessedContent:
    source_content: str
    output_content: str
    metadata: EmbeddedContentMetadata
    attachments: List[ProcessedAttachment]
    is_valid: bool
    error: Optional[str]


class ContentRenderer(Protocol):
    """Protocol for content renderers."""

    def can_render(self, content_type: str, language: str) -> bool:
        """Check if this renderer can handle the content type and language."""
        ...

    def render(self, content: str, settings: Dict, work_dir: Path) -> ProcessedContent:
        """Render the content and return the result."""
        ...


class DiagramRenderer:
    """Renders diagram code into images."""

    def __init__(self, attachment_processor: AttachmentProcessor):
        self.attachment_processor = attachment_processor
        self.supported_types = {
            "mermaid": ["mmdc", "-i", "{input}", "-o", "{output}"],
            "plantuml": ["plantuml", "-tpng", "-output", "{output_dir}", "{input}"],
            "dot": ["dot", "-Tpng", "-o", "{output}", "{input}"],
            "svgbob": ["svgbob", "{input}", "-o", "{output}"],
            "erd": ["erd", "-i", "{input}", "-o", "{output}"],
            "ditaa": ["ditaa", "{input}", "{output}"],
        }

    def can_render(self, content_type: str, language: str) -> bool:
        return content_type == "diagram" and language.lower() in self.supported_types

    def render(self, content: str, settings: Dict, work_dir: Path) -> ProcessedContent:
        try:
            language = settings.get("language", "").lower()
            if language not in self.supported_types:
                raise ValueError(f"Unsupported diagram type: {language}")

            # Create temp files
            input_file = work_dir / f"diagram_{hash(content)}.txt"
            output_file = work_dir / f"diagram_{hash(content)}.png"

            # Write content to input file
            input_file.write_text(content)

            # Get command template
            cmd_template = self.supported_types[language]

            # Build command
            cmd = [
                arg.format(
                    input=str(input_file),
                    output=str(output_file),
                    output_dir=str(output_file.parent),
                )
                for arg in cmd_template
            ]

            # Run command
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Process output file
            processed = self.attachment_processor.process_attachment(
                source_path=output_file,
                embedded=True,
                preview=settings.get("preview", False),
            )

            if not processed.is_valid:
                raise ValueError(f"Failed to process diagram: {processed.error}")

            # Create metadata
            metadata = EmbeddedContentMetadata(
                content_type="diagram",
                language=language,
                line_number=settings.get("line_number", 0),
                context=settings.get("context", ""),
                hash=hashlib.sha256(content.encode()).hexdigest()[:12],
                created=datetime.now(),
                is_preview=settings.get("preview", False),
                settings=settings,
            )

            # Create markdown image reference
            output_content = f"![{language} diagram]({processed.target_path.relative_to(settings['output_dir'])})"

            return ProcessedContent(
                source_content=content,
                output_content=output_content,
                metadata=metadata,
                attachments=[processed],
                is_valid=True,
                error=None,
            )

        except Exception as e:
            logger.error("Diagram rendering failed", error=str(e), language=language)
            return ProcessedContent(
                source_content=content,
                output_content=f"```{language}\n{content}\n```",
                metadata=EmbeddedContentMetadata(
                    content_type="diagram",
                    language=language,
                    line_number=settings.get("line_number", 0),
                    context=settings.get("context", ""),
                    hash="",
                    created=datetime.now(),
                    is_preview=False,
                    settings=settings,
                ),
                attachments=[],
                is_valid=False,
                error=str(e),
            )

        finally:
            # Cleanup temp files
            if input_file.exists():
                input_file.unlink()


class MathRenderer:
    """Renders math equations using KaTeX or MathJax."""

    def __init__(self, attachment_processor: AttachmentProcessor):
        self.attachment_processor = attachment_processor

    def can_render(self, content_type: str, language: str) -> bool:
        return content_type == "math"

    def render(self, content: str, settings: Dict, work_dir: Path) -> ProcessedContent:
        try:
            # Determine if inline or block math
            is_inline = settings.get("inline", False)

            if settings.get("renderer", "katex") == "katex":
                # Use KaTeX for server-side rendering
                output_content = self._render_katex(content, is_inline, settings)
            else:
                # Use MathJax for client-side rendering
                delim = "$" if is_inline else "$$"
                output_content = f"{delim}{content}{delim}"

            metadata = EmbeddedContentMetadata(
                content_type="math",
                language="tex",
                line_number=settings.get("line_number", 0),
                context=settings.get("context", ""),
                hash=hashlib.sha256(content.encode()).hexdigest()[:12],
                created=datetime.now(),
                is_preview=False,
                settings=settings,
            )

            return ProcessedContent(
                source_content=content,
                output_content=output_content,
                metadata=metadata,
                attachments=[],
                is_valid=True,
                error=None,
            )

        except Exception as e:
            logger.error("Math rendering failed", error=str(e))
            delim = "$" if settings.get("inline", False) else "$$"
            return ProcessedContent(
                source_content=content,
                output_content=f"{delim}{content}{delim}",
                metadata=EmbeddedContentMetadata(
                    content_type="math",
                    language="tex",
                    line_number=settings.get("line_number", 0),
                    context=settings.get("context", ""),
                    hash="",
                    created=datetime.now(),
                    is_preview=False,
                    settings=settings,
                ),
                attachments=[],
                is_valid=False,
                error=str(e),
            )

    def _render_katex(self, content: str, is_inline: bool, settings: Dict) -> str:
        """Render math using KaTeX."""
        try:
            import katex

            return katex.render(content, is_inline=is_inline, throw_on_error=False)
        except ImportError:
            # Fall back to client-side rendering
            delim = "$" if is_inline else "$$"
            return f"{delim}{content}{delim}"


class CodeRenderer:
    """Renders code blocks with syntax highlighting."""

    def __init__(self):
        self.supported_languages = {
            "python",
            "javascript",
            "typescript",
            "java",
            "cpp",
            "csharp",
            "go",
            "rust",
            "ruby",
            "php",
            "swift",
            "kotlin",
            "scala",
            "html",
            "css",
            "sql",
            "shell",
            "bash",
            "powershell",
            "yaml",
            "json",
            "xml",
            "markdown",
            "tex",
            "r",
            "matlab",
            "perl",
        }

    def can_render(self, content_type: str, language: str) -> bool:
        return content_type == "code" and language.lower() in self.supported_languages

    def render(self, content: str, settings: Dict, work_dir: Path) -> ProcessedContent:
        try:
            language = settings.get("language", "").lower()

            # Apply syntax highlighting
            if settings.get("highlight", True):
                output_content = self._highlight_code(content, language, settings)
            else:
                output_content = f"```{language}\n{content}\n```"

            metadata = EmbeddedContentMetadata(
                content_type="code",
                language=language,
                line_number=settings.get("line_number", 0),
                context=settings.get("context", ""),
                hash=hashlib.sha256(content.encode()).hexdigest()[:12],
                created=datetime.now(),
                is_preview=False,
                settings=settings,
            )

            return ProcessedContent(
                source_content=content,
                output_content=output_content,
                metadata=metadata,
                attachments=[],
                is_valid=True,
                error=None,
            )

        except Exception as e:
            logger.error("Code rendering failed", error=str(e), language=language)
            return ProcessedContent(
                source_content=content,
                output_content=f"```{language}\n{content}\n```",
                metadata=EmbeddedContentMetadata(
                    content_type="code",
                    language=language,
                    line_number=settings.get("line_number", 0),
                    context=settings.get("context", ""),
                    hash="",
                    created=datetime.now(),
                    is_preview=False,
                    settings=settings,
                ),
                attachments=[],
                is_valid=False,
                error=str(e),
            )

    def _highlight_code(self, content: str, language: str, settings: Dict) -> str:
        """Apply syntax highlighting to code."""
        try:
            import pygments
            from pygments import highlight
            from pygments.formatters import HtmlFormatter
            from pygments.lexers import get_lexer_by_name

            # Get lexer for language
            lexer = get_lexer_by_name(language)

            # Configure formatter
            formatter = HtmlFormatter(
                style=settings.get("style", "default"),
                linenos=settings.get("line_numbers", False),
                cssclass=settings.get("css_class", "highlight"),
                wrapcode=True,
            )

            # Highlight code
            highlighted = highlight(content, lexer, formatter)

            return f'<div class="code-block">{highlighted}</div>'

        except ImportError:
            # Fall back to plain code block
            return f"```{language}\n{content}\n```"


class EmbeddedContentProcessor:
    """Processes embedded content in markdown documents."""

    def __init__(
        self,
        attachment_processor: AttachmentProcessor,
        work_dir: Path,
        output_dir: Path,
    ):
        self.attachment_processor = attachment_processor
        self.work_dir = work_dir
        self.output_dir = output_dir

        # Initialize renderers
        self.renderers: List[ContentRenderer] = [
            DiagramRenderer(attachment_processor),
            MathRenderer(attachment_processor),
            CodeRenderer(),
        ]

        # Track processed content
        self.processed: Dict[str, ProcessedContent] = {}

    def process_content(
        self,
        content: str,
        content_type: str,
        language: str,
        line_number: int,
        context: str,
        settings: Optional[Dict] = None,
    ) -> ProcessedContent:
        """Process embedded content and return the result."""
        try:
            # Merge settings
            full_settings = {
                "line_number": line_number,
                "context": context,
                "output_dir": self.output_dir,
            }
            if settings:
                full_settings.update(settings)

            # Generate content hash
            content_hash = hashlib.sha256(
                f"{content_type}:{language}:{content}".encode()
            ).hexdigest()[:12]

            # Return cached result if available
            if content_hash in self.processed:
                return self.processed[content_hash]

            # Find suitable renderer
            renderer = next(
                (r for r in self.renderers if r.can_render(content_type, language)),
                None,
            )

            if not renderer:
                raise ValueError(f"No renderer found for {content_type}:{language}")

            # Render content
            result = renderer.render(content, full_settings, self.work_dir)

            # Cache result
            self.processed[content_hash] = result

            return result

        except Exception as e:
            logger.error(
                "Content processing failed",
                error=str(e),
                content_type=content_type,
                language=language,
            )
            return ProcessedContent(
                source_content=content,
                output_content=f"```{language}\n{content}\n```",
                metadata=EmbeddedContentMetadata(
                    content_type=content_type,
                    language=language,
                    line_number=line_number,
                    context=context,
                    hash="",
                    created=datetime.now(),
                    is_preview=False,
                    settings=settings or {},
                ),
                attachments=[],
                is_valid=False,
                error=str(e),
            )

    def get_processed_attachments(self) -> List[ProcessedAttachment]:
        """Get all processed attachments."""
        attachments = []
        for content in self.processed.values():
            attachments.extend(content.attachments)
        return attachments

    def cleanup(self):
        """Clean up temporary files."""
        try:
            import shutil

            for item in self.work_dir.glob("*"):
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
        except Exception as e:
            logger.error("Cleanup failed", error=str(e))


__all__ = ["EmbeddedContentProcessor", "ProcessedContent", "EmbeddedContentMetadata"]
