from pathlib import Path
import weasyprint
from typing import Dict, Any
from .config import NovaConfig
from .logging import get_logger
import markdown
import aiofiles
import re

logger = get_logger(__name__)

# PDF Styling
PDF_STYLES = """
/* Base document styles */
@page {
    margin: 2.5cm 1.5cm;
    @top-right {
        content: counter(page);
    }
}

body {
    font-family: 'Helvetica', sans-serif;
    line-height: 1.5;
    font-size: 11pt;
}

/* Headers */
h1 {
    font-size: 24pt;
    margin-top: 2em;
    page-break-before: always;
    page-break-after: avoid;
    border-bottom: 1px solid #eee;
    padding-bottom: 0.5em;
}

h2 {
    font-size: 18pt;
    margin-top: 1.5em;
    page-break-inside: avoid;
    page-break-after: avoid;
    margin-bottom: 1em;
}

/* Lists */
ul, ol {
    margin-left: 2em;
    padding-left: 0;
    margin-bottom: 1em;
    list-style-position: outside;
}

li {
    margin-bottom: 0.5em;
    line-height: 1.4;
    padding-left: 0.5em;
}

/* Nested lists */
li > ul, li > ol {
    margin-top: 0.5em;
    margin-bottom: 0;
    margin-left: 1em;
}

/* Fix bullet points */
ul > li {
    list-style-type: disc;
}

ul ul > li {
    list-style-type: circle;
}

ul ul ul > li {
    list-style-type: square;
}

/* Task Lists */
.task-list {
    list-style-type: none;
    padding-left: 1.5em;
}

.task-list li {
    text-indent: -1.5em;
}

/* Code Blocks */
pre {
    background-color: #f6f8fa;
    padding: 1em;
    border-radius: 4px;
    font-family: 'Courier', monospace;
    font-size: 9pt;
    white-space: pre-wrap;
    page-break-inside: avoid;
}

/* Metadata Comments */
comment, .comment, *[class^="metadata-"] {
    display: none !important;
}

/* Hide all HTML comments */
.comment-node {
    display: none !important;
}

/* Hide comment markers */
*:before, *:after {
    content: none !important;
}

/* Section Breaks */
hr {
    border: none;
    border-top-width: 1px;
    border-top-style: solid;
    border-top-color: #000000;
    margin: 2em 0;
    page-break-after: avoid;
}

/* Links */
a {
    color: #0366d6;
    text-decoration: none;
}

/* Tables */
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

/* Embedded Document References */
.embedded-doc {
    background-color: #f8f9fa;
    padding: 1em;
    margin: 1em 0;
    border-left: 4px solid #0366d6;
    page-break-inside: avoid;
}

/* Avoid orphans and widows */
p, li {
    orphans: 3;
    widows: 3;
}
"""

async def generate_pdf(input_file: Path, output_file: Path, config: NovaConfig) -> bool:
    try:
        # Convert input_file and output_file to strings if they're OptionInfo objects
        input_path = str(input_file) if input_file else None
        output_path = str(output_file) if output_file else None
        
        if not input_path or not output_path:
            logger.error("pdf_generation_failed", error="Invalid input or output path")
            return False

        # Read markdown content
        async with aiofiles.open(input_path, 'r', encoding='utf-8') as f:
            content = await f.read()

        # Convert markdown to HTML
        html_content = markdown.markdown(
            content,
            extensions=['tables', 'fenced_code']
        )

        # Create full HTML document
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Generate PDF with updated styles
        weasyprint.HTML(string=html).write_pdf(
            output_path,
            stylesheets=[weasyprint.CSS(string=PDF_STYLES)]
        )
        
        logger.info("pdf_generated", output_path=output_path)
        return True
        
    except Exception as e:
        logger.error("pdf_generation_failed", error=str(e))
        return False 