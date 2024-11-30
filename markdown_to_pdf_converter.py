#!/usr/bin/env python3

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
import markdown
import jinja2
from weasyprint import HTML, CSS
from bs4 import BeautifulSoup
from datetime import datetime

from colors import NovaConsole
from src.utils.timing import timed_section
from src.utils.path_utils import normalize_path, format_path

# Initialize console
nova_console = NovaConsole()

class PDFConverter:
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize PDF converter with optional config."""
        self.config = self.load_config(config_path)
        self.template_env = self.setup_jinja()
        
    def load_config(self, config_path: Optional[Path]) -> Dict[Any, Any]:
        """Load configuration from YAML file."""
        default_config = {
            'template': 'default_template.html',
            'style': 'default_style.css',
            'pdf': {
                'margin': '1in',
                'page-size': 'Letter'
            }
        }
        
        if not config_path:
            return default_config
            
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
            return {**default_config, **config}
        except Exception as e:
            nova_console.warning(f"Failed to load config: {e}. Using defaults.")
            return default_config
            
    def setup_jinja(self) -> jinja2.Environment:
        """Setup Jinja2 environment."""
        template_dir = Path(__file__).parent / 'templates'
        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=True
        )
        
    @timed_section("Loading content")
    def load_content(self, input_file: Path) -> str:
        """Load and clean content from file."""
        content = input_file.read_text(encoding='utf-8')
        return self.clean_content(content)
        
    @timed_section("Converting markdown")
    def convert_markdown(self, content: str) -> tuple[str, str]:
        """Convert markdown to HTML and generate TOC."""
        md = markdown.Markdown(extensions=['extra', 'toc', 'tables', 'fenced_code'])
        html = md.convert(content)
        return html, md.toc
        
    @timed_section("Generating PDF")
    def generate_pdf(self, html: str, output_file: Path, css: CSS) -> None:
        """Generate PDF from HTML."""
        HTML(string=html).write_pdf(output_file, stylesheets=[css], **self.config['pdf'])
        
    def convert(self, input_file: Path, output_file: Path) -> bool:
        """Convert markdown to PDF."""
        try:
            # Ensure output directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Start conversion
            nova_console.process_start("PDF conversion", str(input_file))
            
            # Load and convert content
            content = self.load_content(input_file)
            html, toc = self.convert_markdown(content)
            
            # Generate PDF
            template = self.template_env.get_template(self.config['template'])
            context = {
                'content': html,
                'title': input_file.stem,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'toc': toc
            }
            
            rendered = template.render(**context)
            rendered = self.clean_html(rendered)
            
            style_path = Path(__file__).parent / 'styles' / self.config['style']
            css = CSS(filename=str(style_path))
            
            self.generate_pdf(rendered, output_file, css)
            
            # Show completion stats
            size_mb = output_file.stat().st_size / (1024 * 1024)
            nova_console.process_complete("PDF conversion", {
                "Output": str(output_file),
                "Size": f"{size_mb:.1f}MB"
            })
            return True
            
        except Exception as e:
            nova_console.error("PDF conversion failed", str(e))
            return False

    def clean_content(self, content: str) -> str:
        """Clean markdown content of problematic characters."""
        # Replace Unicode line separators with standard newlines
        content = content.replace('\u2028', '\n').replace('\u2029', '\n')
        
        # Normalize line endings
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove zero-width spaces
        content = content.replace('\u200b', '')
        
        # Ensure single newline between paragraphs
        content = '\n\n'.join(p.strip() for p in content.split('\n\n'))
        
        return content

    def clean_html(self, html: str) -> str:
        """Clean HTML content before PDF generation."""
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove empty paragraphs
        for p in soup.find_all('p'):
            if not p.get_text(strip=True):
                p.decompose()
        
        # Ensure proper spacing
        return str(soup.prettify())

def main():
    """CLI entry point."""
    if len(sys.argv) < 3:
        nova_console.error("Usage: python markdown_to_pdf_converter.py <input_file> <output_file>")
        sys.exit(1)
        
    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    
    if not input_file.exists():
        nova_console.error(f"Input file not found: {input_file}")
        sys.exit(1)
        
    converter = PDFConverter()
    success = converter.convert(input_file, output_file)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()