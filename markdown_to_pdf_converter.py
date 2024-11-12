import click
import logging
from pathlib import Path
from typing import Optional, Tuple
import yaml
import markdown
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
from datetime import datetime
import os
from rich import print
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import sys
from colors import Colors, console

# Get the directory where the script is located
SCRIPT_DIR = Path(__file__).parent

# Utility Functions

def load_config(config_path: Optional[Path], logger: logging.Logger) -> dict:
    default_config_path = SCRIPT_DIR / 'config/default_config.yaml'
    try:
        if config_path and config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {config_path}")
        else:
            with open(default_config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info("Loaded default configuration")
        return config
    except Exception as e:
        logger.error(f"Invalid configuration file: {e}")
        raise ValueError("Invalid configuration file")

def validate_input(input_path: Path, config: dict, logger: logging.Logger) -> None:
    if not input_path.exists():
        logger.error(f"Markdown file not found: {input_path}")
        raise FileNotFoundError(f"Markdown file not found: {input_path}")
    # Additional validations can be added here

def read_markdown_file(file_path: Path, logger: logging.Logger) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Clean problematic Unicode characters
        content = content.replace('\u2029', '\n')  # Replace paragraph separator
        content = content.replace('\u2028', '\n')  # Replace line separator
        # Normalize line endings
        content = '\n'.join(line.rstrip() for line in content.splitlines())
        logger.info(f"Read markdown file: {file_path}")
        return content
    except Exception as e:
        logger.error(f"Error reading markdown file: {e}")
        raise e

def process_markdown(content: str, config: dict, logger: logging.Logger, base_path: Path) -> Tuple[str, dict, markdown.Markdown]:
    """
    Process markdown content to HTML and extract metadata.
    
    Args:
        content (str): The markdown content.
        config (dict): Configuration dictionary.
        logger (logging.Logger): Logger for logging messages.
        base_path (Path): Base path for resolving relative image paths.
    
    Returns:
        Tuple[str, dict, markdown.Markdown]: HTML content, metadata, and markdown object.
    """
    try:
        extensions = ['extra', 'meta']
        if config['toc']['enabled']:
            extensions.append('toc')
        md = markdown.Markdown(extensions=extensions)
        html_body = md.convert(content)
        
        # Resolve image paths
        html_body = resolve_image_paths(html_body, base_path)
        
        metadata = md.Meta if hasattr(md, 'Meta') else {}
        logger.info("Processed markdown content")
        return html_body, metadata, md
    except Exception as e:
        logger.error(f"Markdown processing error: {e}")
        raise e

def resolve_image_paths(html_content: str, base_path: Path) -> str:
    """
    Resolve relative image paths in HTML content to absolute paths.
    
    Args:
        html_content (str): The HTML content with potential relative image paths.
        base_path (Path): The base path to resolve relative paths.
    
    Returns:
        str: HTML content with resolved image paths.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    for img in soup.find_all('img'):
        src = img.get('src')
        if src and not src.startswith(('http://', 'https://')):
            img['src'] = urljoin(f'file://{base_path}/', src)
    return str(soup)

def generate_html(
    content: str,
    template_path: Path,
    config: dict,
    metadata: dict,
    md: markdown.Markdown,
    style_path: Optional[Path],
    logger: logging.Logger
) -> str:
    try:
        if not template_path.exists():
            template_path = SCRIPT_DIR / 'templates/default_template.html'
        env = Environment(loader=FileSystemLoader(template_path.parent))
        template = env.get_template(template_path.name)

        if style_path and style_path.exists():
            with open(style_path, 'r') as f:
                styles = f.read()
            logger.info(f"Using custom style from {style_path}")
        else:
            default_style_path = SCRIPT_DIR / 'styles/default_style.css'
            with open(default_style_path, 'r') as f:
                styles = f.read()
            logger.info("Using default styles")

        toc = ''
        if config['toc']['enabled']:
            toc = md.toc

        html_content = template.render(
            content=content,
            styles=styles,
            config=config,
            metadata=metadata,
            toc=toc
        )
        logger.info("Generated HTML content")
        return html_content
    except Exception as e:
        logger.error(f"HTML generation error: {e}")
        raise e

def generate_pdf(html_content: str, output_path: Path, config: dict, logger: logging.Logger) -> None:
    try:
        html = HTML(string=html_content)
        css = CSS(string='@page { size: %s; margin: %s; }' % (
            config['style']['page_size'],
            config['style']['margin']
        ))
        html.write_pdf(target=str(output_path), stylesheets=[css])
        
        # Verify PDF was created and has content
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("PDF generation failed: Output file is empty or not created")
            
        logger.info(f"Generated PDF at {output_path}")
    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        raise e

def apply_pdf_metadata(pdf_path: Path, metadata: dict, logger: logging.Logger) -> None:
    try:
        # Placeholder for metadata application logic
        logger.info(f"Applied metadata to PDF at {pdf_path}")
    except Exception as e:
        logger.error(f"Error applying metadata to PDF: {e}")
        raise e

# Converter Class

class MarkdownToPDFConverter:
    def __init__(
        self,
        input_path: Path,
        output_path: Path,
        config_path: Optional[Path],
        style_path: Optional[Path],
        toc_enabled: Optional[bool],
        verbose: bool
    ):
        self.input_path = input_path
        self.output_path = output_path
        self.config_path = config_path
        self.style_path = style_path
        self.toc_enabled = toc_enabled
        self.verbose = verbose
        self.config = {}
        self.metadata = {}
        self.html_content = ''
        self.logger = self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            filename='markdown_to_pdf.log',
            level=logging.DEBUG if self.verbose else logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)

    def convert(self):
        self.logger.info("Starting conversion process.")
        self.config = load_config(self.config_path, self.logger)
        if self.toc_enabled is not None:
            self.config['toc']['enabled'] = self.toc_enabled

        validate_input(self.input_path, self.config, self.logger)

        markdown_content = read_markdown_file(self.input_path, self.logger)
        html_body, metadata, md = process_markdown(markdown_content, self.config, self.logger, self.input_path.parent)

        self.metadata = {
            'title': metadata.get('title', self.input_path.stem),
            'author': metadata.get('author', ''),
            'created_date': datetime.now().isoformat(),
            'source_file': str(self.input_path)
        }

        self.html_content = generate_html(
            content=html_body,
            template_path=self.config.get('template_path', SCRIPT_DIR / 'templates/default_template.html'),
            config=self.config,
            metadata=self.metadata,
            md=md,
            style_path=self.style_path,
            logger=self.logger
        )

        generate_pdf(
            html_content=self.html_content,
            output_path=self.output_path,
            config=self.config,
            logger=self.logger
        )

        apply_pdf_metadata(
            pdf_path=self.output_path,
            metadata=self.metadata,
            logger=self.logger
        )

        self.logger.info("Conversion process completed successfully.")

# CLI Interface

def convert_markdown_to_pdf(input_path: Path, output_path: Path, config_path: Optional[Path], style_path: Optional[Path]) -> None:
    """Convert markdown to PDF with minimal console output."""
    try:
        Colors.header("Converting Markdown to PDF")
        
        # Setup logging
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        Colors.info("Loading configuration...")
        config = load_config(config_path, logger)
        
        Colors.info("Processing markdown content...")
        content = read_markdown_file(input_path, logger)
        html_body, metadata, md = process_markdown(content, config, logger, input_path.parent)
        
        Colors.info("Generating HTML...")
        template_path = config.get('template_path', SCRIPT_DIR / 'templates/default_template.html')
        if isinstance(template_path, str):
            template_path = Path(template_path)
        
        html_content = generate_html(
            content=html_body,
            template_path=template_path,
            config=config,
            metadata=metadata,
            md=md,
            style_path=style_path,
            logger=logger
        )
        
        Colors.info("Creating PDF...")
        generate_pdf(html_content, output_path, config, logger)
        
        Colors.success("PDF created successfully")
        Colors.info(f"Location: {output_path}")
        Colors.info(f"Size: {output_path.stat().st_size / 1024:.1f}KB")
        
    except Exception as e:
        Colors.error(f"Conversion error: {str(e)}")
        logger.error(f"Conversion error: {e}")
        raise e

@click.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path(), required=False)
@click.option('--config', type=click.Path(exists=True), help='Path to YAML config file')
@click.option('--style', type=click.Path(exists=True), help='Path to custom CSS file')
@click.option('--toc/--no-toc', default=None, help='Enable/disable table of contents')
@click.option('--verbose', is_flag=True, help='Increase output verbosity')
def main(input_file, output_file, config, style, toc, verbose):
    """Converts a Markdown file to a professionally formatted PDF."""
    try:
        input_path = Path(input_file)
        output_path = Path(output_file) if output_file else input_path.with_suffix('.pdf')
        config_path = Path(config) if config else None
        style_path = Path(style) if style else None

        convert_markdown_to_pdf(input_path, output_path, config_path, style_path)
        
        if not output_path.exists() or output_path.stat().st_size == 0:
            Colors.error("PDF generation failed")
            sys.exit(1)
            
        Colors.success(f"PDF generated successfully at {output_path}")
        Colors.info(f"Size: {output_path.stat().st_size / 1024:.1f}KB")
        
    except Exception as e:
        Colors.error(f"Error: {str(e)}")
        sys.exit(1)

# Entry Point
if __name__ == '__main__':
    main()