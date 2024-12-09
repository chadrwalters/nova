from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import structlog
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.core.exceptions import TemplateError

logger = structlog.get_logger(__name__)


@dataclass
class Template:
    """Represents an HTML template."""

    name: str
    required_placeholders: set[str]


class TemplateManager:
    """Manages HTML templates for document processing."""

    def __init__(self, template_dir: Path):
        self.template_dir = template_dir
        self.templates: Dict[str, Template] = {}
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self._load_templates()

    def _load_templates(self) -> None:
        """Load all templates from template directory."""
        try:
            # Define required placeholders for each template
            template_specs = {
                "single_page.html": {
                    "required": {
                        "title",
                        "content",
                        "source_file",
                        "last_updated",
                        "media_path",
                    }
                },
                "combined_page.html": {
                    "required": {"title", "content", "last_updated", "media_path"}
                },
            }

            # Load and validate each template
            for template_name, specs in template_specs.items():
                template_path = self.template_dir / template_name
                if not template_path.exists():
                    raise TemplateError(f"Template not found: {template_name}")

                try:
                    # Just verify the template exists and can be loaded
                    self.env.get_template(template_name)
                except Exception as e:
                    raise TemplateError(
                        f"Failed to load template {template_name}: {str(e)}"
                    )

                self.templates[template_name] = Template(
                    name=template_name, required_placeholders=specs["required"]
                )
        except Exception as e:
            if not isinstance(e, TemplateError):
                raise TemplateError(f"Template initialization failed: {str(e)}")
            raise

    def get_template(self, name: str) -> Template:
        """Get a template by name."""
        if name not in self.templates:
            raise ValueError(f"Template not found: {name}")
        return self.templates[name]

    def validate_template_args(self, template_name: str, **kwargs) -> None:
        """Validate template arguments."""
        template = self.get_template(template_name)
        missing = template.required_placeholders - set(kwargs.keys())
        if missing:
            raise TemplateError(
                f"Missing required placeholders for {template_name}: {missing}"
            )

    def render(self, template_name: str, **kwargs) -> str:
        """Render a template with the given arguments."""
        self.validate_template_args(template_name, **kwargs)
        template = self.env.get_template(template_name)

        # Add default styles if not provided
        if "styles" not in kwargs:
            kwargs["styles"] = self._get_default_styles()

        return template.render(**kwargs)

    def _get_default_styles(self) -> str:
        """Get default CSS styles for HTML output."""
        return """
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 2rem;
            }

            /* Headers */
            .section-header {
                margin-top: 2em;
                margin-bottom: 1em;
                color: #2c3e50;
                border-bottom: 2px solid #eee;
                padding-bottom: 0.3em;
            }

            h1.section-header { font-size: 2.2em; }
            h2.section-header { font-size: 1.8em; }
            h3.section-header { font-size: 1.5em; }
            h4.section-header { font-size: 1.3em; }
            h5.section-header { font-size: 1.2em; }
            h6.section-header { font-size: 1.1em; }

            /* Paragraphs */
            .content-paragraph {
                margin: 1em 0;
                text-align: justify;
            }

            /* Lists */
            .spaced-list {
                margin: 1em 0;
                padding-left: 2em;
                list-style-type: disc;
            }

            .spaced-list li {
                margin: 0.5em 0;
                padding-left: 0.5em;
            }

            .nested-list {
                margin: 0.5em 0;
                padding-left: 2em;
                list-style-type: circle;
            }

            .nested-list .nested-list {
                list-style-type: square;
            }

            /* Code blocks */
            .code-block {
                background-color: #f8f9fa;
                border: 1px solid #eee;
                border-radius: 4px;
                padding: 1em;
                margin: 1em 0;
                overflow-x: auto;
                font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
            }

            /* Inline code */
            code {
                background-color: #f8f9fa;
                padding: 0.2em 0.4em;
                border-radius: 3px;
                font-size: 0.9em;
                font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
            }

            /* Links */
            a {
                color: #0366d6;
                text-decoration: none;
            }

            a:hover {
                text-decoration: underline;
            }

            /* Tables */
            table {
                border-collapse: collapse;
                width: 100%;
                margin: 1em 0;
            }

            th, td {
                border: 1px solid #dfe2e5;
                padding: 0.6em 1em;
                text-align: left;
            }

            th {
                background-color: #f6f8fa;
                font-weight: 600;
            }

            tr:nth-child(even) {
                background-color: #f8f9fa;
            }

            /* Blockquotes */
            blockquote {
                margin: 1em 0;
                padding: 0 1em;
                color: #6a737d;
                border-left: 0.25em solid #dfe2e5;
            }

            /* Images */
            img {
                max-width: 100%;
                height: auto;
                margin: 1em 0;
                border-radius: 4px;
            }

            /* Metadata */
            .metadata {
                margin-bottom: 2em;
                color: #6a737d;
                font-size: 0.9em;
            }

            .metadata p {
                margin: 0.5em 0;
            }

            /* Strikethrough */
            .strikethrough {
                text-decoration: line-through;
                color: #6a737d;
            }

            /* Task Lists */
            .task-list {
                list-style-type: none;
                padding-left: 0;
            }

            .task-list-item {
                margin: 0.5em 0;
                display: flex;
                align-items: center;
            }

            .task-list-item input[type="checkbox"] {
                margin-right: 0.5em;
            }

            /* Emphasis */
            em {
                font-style: italic;
            }

            strong {
                font-weight: 600;
            }
        """
