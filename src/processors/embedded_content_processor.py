# mypy: disable-error-code="no-any-return"
import hashlib
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Set, TypedDict, Union, cast

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
    settings: Dict[str, Any]


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
        """Check if this renderer can handle the content type and language.

        Args:
            content_type: Type of content to render
            language: Language of the content

        Returns:
            True if this renderer can handle the content, False otherwise
        """
        ...

    def render(
        self, content: str, settings: Dict[str, Any], work_dir: Path
    ) -> ProcessedContent:
        """Render the content and return the result.

        Args:
            content: Content to render
            settings: Rendering settings
            work_dir: Working directory for temporary files

        Returns:
            Processed content with metadata and attachments
        """
        ...


class DiagramRenderer:
    """Renders diagram code into images."""

    def __init__(self, attachment_processor: AttachmentProcessor) -> None:
        """Initialize the diagram renderer.

        Args:
            attachment_processor: Processor for handling attachments
        """
        self.attachment_processor = attachment_processor
        self.supported_types: Dict[str, List[str]] = {
            "mermaid": ["mmdc", "-i", "{input}", "-o", "{output}"],
            "plantuml": ["plantuml", "-tpng", "-output", "{output_dir}", "{input}"],
            "dot": ["dot", "-Tpng", "-o", "{output}", "{input}"],
            "svgbob": ["svgbob", "{input}", "-o", "{output}"],
            "erd": ["erd", "-i", "{input}", "-o", "{output}"],
            "ditaa": ["ditaa", "{input}", "{output}"],
        }

    def can_render(self, content_type: str, language: str) -> bool:
        """Check if this renderer can handle the content type and language.

        Args:
            content_type: Type of content to render
            language: Language of the content

        Returns:
            True if this renderer can handle the content, False otherwise
        """
        return content_type == "diagram" and language.lower() in self.supported_types

    def render(
        self, content: str, settings: Dict[str, Any], work_dir: Path
    ) -> ProcessedContent:
        """Render diagram content into an image.

        Args:
            content: Diagram content to render
            settings: Rendering settings
            work_dir: Working directory for temporary files

        Returns:
            Processed content with metadata and attachments
        """
        input_file: Optional[Path] = None
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
                file_path=output_file, target_name=f"diagram_{hash(content)}.png"
            )

            if not processed:
                raise ValueError("Failed to process diagram: Unknown error")

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
            relative_path = processed.target_path.relative_to(settings["output_dir"])
            output_content = f"![{language} diagram]({relative_path})"

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
            if input_file and input_file.exists():
                input_file.unlink()


class MathRenderer:
    """Renders math equations using KaTeX or MathJax."""

    def __init__(self, attachment_processor: AttachmentProcessor) -> None:
        """Initialize the math renderer.

        Args:
            attachment_processor: Processor for handling attachments
        """
        self.attachment_processor = attachment_processor

    def can_render(self, content_type: str, language: str) -> bool:
        """Check if this renderer can handle the content type and language.

        Args:
            content_type: Type of content to render
            language: Language of the content

        Returns:
            True if this renderer can handle the content, False otherwise
        """
        return content_type == "math"

    def render(
        self, content: str, settings: Dict[str, Any], work_dir: Path
    ) -> ProcessedContent:
        """Render math content using KaTeX or MathJax.

        Args:
            content: Math content to render
            settings: Rendering settings
            work_dir: Working directory for temporary files

        Returns:
            Processed content with metadata and attachments
        """
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

    def _render_katex(
        self, content: str, is_inline: bool, settings: Dict[str, Any]
    ) -> str:
        """Render math using KaTeX.

        Args:
            content: Math content to render
            is_inline: Whether to render inline or block math
            settings: Rendering settings

        Returns:
            Rendered math content
        """
        try:
            import katex

            return katex.render(content, is_inline=is_inline, throw_on_error=False)
        except ImportError:
            # Fall back to client-side rendering
            delim = "$" if is_inline else "$$"
            return f"{delim}{content}{delim}"


class CodeRenderer:
    """Renders code blocks with syntax highlighting."""

    def __init__(self) -> None:
        """Initialize the code renderer."""
        self.supported_languages: Set[str] = {
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
        }

    def can_render(self, content_type: str, language: str) -> bool:
        """Check if this renderer can handle the content type and language.

        Args:
            content_type: Type of content to render
            language: Language of the content

        Returns:
            True if this renderer can handle the content, False otherwise
        """
        return content_type == "code" and language.lower() in self.supported_languages

    def render(
        self, content: str, settings: Dict[str, Any], work_dir: Path
    ) -> ProcessedContent:
        """Render code content with syntax highlighting.

        Args:
            content: Code content to render
            settings: Rendering settings
            work_dir: Working directory for temporary files

        Returns:
            Processed content with metadata and attachments
        """
        try:
            language = settings.get("language", "").lower()
            if language not in self.supported_languages:
                raise ValueError(f"Unsupported language: {language}")

            # Apply syntax highlighting
            output_content = self._highlight_code(content, language, settings)

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
            logger.error("Code rendering failed", error=str(e))
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

    def _highlight_code(
        self, content: str, language: str, settings: Dict[str, Any]
    ) -> str:
        """Apply syntax highlighting to code.

        Args:
            content: Code content to highlight
            language: Programming language
            settings: Highlighting settings

        Returns:
            Highlighted code HTML
        """
        try:
            from pygments import formatters
            from pygments import highlight as pygments_highlight
            from pygments import lexers

            # Get lexer for language
            lexer = lexers.get_lexer_by_name(language)

            # Configure formatter
            formatter = formatters.HtmlFormatter(
                linenos=settings.get("line_numbers", True),
                cssclass=settings.get("css_class", "highlight"),
                style=settings.get("style", "monokai"),
            )

            # Highlight code and ensure string type
            # Note: Pygments lacks type hints
            try:
                highlighted = pygments_highlight(  # type: ignore[no-any-return]
                    content, lexer, formatter
                )
                if not highlighted or not isinstance(highlighted, str):
                    raise ValueError("Invalid highlight result")
                return highlighted  # type: ignore[no-any-return]

            except Exception:
                logger.warning("Pygments highlight failed")
                return self._fallback_code_block(content, language)

        except Exception as e:
            # Fall back to plain code block
            logger.warning(f"Code highlighting failed: {str(e)}")
            return self._fallback_code_block(content, language)

    def _fallback_code_block(
        self, content: str, language: str
    ) -> str:  # type: ignore[no-any-return]
        """Create a fallback code block when highlighting fails.

        Args:
            content: Code content to format
            language: Programming language

        Returns:
            Markdown code block
        """
        return f"```{language}\n{content}\n```"


class EmbeddedContentProcessor:
    """Processes embedded content in markdown documents."""

    def __init__(self, attachment_processor: AttachmentProcessor) -> None:
        """Initialize the embedded content processor.

        Args:
            attachment_processor: Processor for handling attachments
        """
        self.attachment_processor = attachment_processor
        self.renderers: List[Union[DiagramRenderer, MathRenderer, CodeRenderer]] = [
            DiagramRenderer(attachment_processor),
            MathRenderer(attachment_processor),
            CodeRenderer(),
        ]

    def process_content(
        self,
        content: str,
        content_type: str,
        language: str,
        settings: Dict[str, Any],
        work_dir: Path,
    ) -> ProcessedContent:
        """Process embedded content.

        Args:
            content: Content to process
            content_type: Type of content
            language: Content language
            settings: Processing settings
            work_dir: Working directory for temporary files

        Returns:
            Processed content with metadata and attachments
        """
        try:
            # Find suitable renderer
            renderer = next(
                (r for r in self.renderers if r.can_render(content_type, language)),
                None,
            )

            if not renderer:
                raise ValueError(f"No renderer found for {content_type}/{language}")

            # Render content
            result = renderer.render(content, settings, work_dir)
            return result

        except Exception as e:
            logger.error("Content processing failed", error=str(e))
            return ProcessedContent(
                source_content=content,
                output_content=f"```{language}\n{content}\n```",
                metadata=EmbeddedContentMetadata(
                    content_type=content_type,
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

    def cleanup(self) -> None:
        """Clean up temporary files."""
        pass  # No cleanup needed in this implementation


__all__ = ["EmbeddedContentProcessor", "ProcessedContent", "EmbeddedContentMetadata"]
