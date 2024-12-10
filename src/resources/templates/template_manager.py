from pathlib import Path
from typing import Optional

class TemplateManager:
    """Manages HTML templates for document processing."""

    def __init__(self, template_dir: Path) -> None:
        """Initialize the template manager.

        Args:
            template_dir: Directory containing HTML templates
        """
        self.template_dir = template_dir
        self.template_path = template_dir / "template.html"
        
        # Create default template if it doesn't exist
        if not self.template_path.exists():
            self._create_default_template()

    def apply_template(self, content: str) -> str:
        """Apply HTML template to content.

        Args:
            content: HTML content to wrap in template

        Returns:
            Content wrapped in HTML template
        """
        template = self.template_path.read_text(encoding="utf-8")
        return template.replace("{{content}}", content).replace("{{title}}", "Consolidated Document")

    def _create_default_template(self) -> None:
        """Create a default HTML template."""
        default_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{title}}</title>
    <style>
        @page {
            size: letter;
            margin: 2cm;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            color: #333;
        }
        img {
            max-width: 100%;
            height: auto;
            page-break-inside: avoid;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #2c3e50;
            margin-top: 2rem;
            page-break-after: avoid;
        }
        code {
            background-color: #f5f5f5;
            padding: 0.2em 0.4em;
            border-radius: 3px;
            font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
        }
        pre {
            background-color: #f5f5f5;
            padding: 1rem;
            border-radius: 5px;
            overflow-x: auto;
            page-break-inside: avoid;
        }
        blockquote {
            border-left: 4px solid #ddd;
            margin: 0;
            padding-left: 1rem;
            color: #666;
            page-break-inside: avoid;
        }
        hr {
            border: none;
            border-top: 2px solid #ddd;
            margin: 2rem 0;
        }
        a {
            color: #3498db;
            text-decoration: none;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 1rem 0;
            page-break-inside: avoid;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 0.5rem;
            text-align: left;
        }
        th {
            background-color: #f5f5f5;
        }
        @media print {
            body {
                font-size: 12pt;
            }
            a {
                text-decoration: none;
                color: #000;
            }
            pre, code {
                font-size: 10pt;
            }
        }
    </style>
</head>
<body>
    {{content}}
</body>
</html>"""
        self.template_path.write_text(default_template, encoding="utf-8")