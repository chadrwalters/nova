import typer
import asyncio
import sys
from pathlib import Path
from typing import Optional
from typer import Option
import structlog
from ..core.config import NovaConfig
from ..core.validation import load_config
from ..core.logging import configure_logging, get_logger
from ..core.errors import NovaError, ConfigError
from ..pipeline.markdown import process_markdown_files
from ..pipeline.consolidate import consolidate_markdown
from ..processors.pdf_generator import generate_pdf_files

# Create Typer app
app = typer.Typer()

# Initialize logger - will be configured properly after config is loaded
logger = get_logger(__name__)

def setup_environment(config_path: Optional[Path] = None) -> NovaConfig:
    """Set up the environment and load configuration."""
    try:
        # Load configuration
        if config_path is None:
            config_path = Path("config/default_config.yaml")
        
        if not config_path.is_file():
            raise ConfigError(f"Configuration file not found: {config_path}")
            
        config = load_config(config_path)
        
        # Configure logging
        configure_logging(config)
        
        # Validate system resources
        config.validate_system_resources()
        
        return config
        
    except Exception as e:
        logger.error("setup_failed", 
                    error=str(e),
                    config_path=str(config_path))
        raise

@app.command()
def process_markdown(
    input_dir: str = Option(None, "--input", help="Input directory containing markdown files"),
    output: str = Option(None, help="Output directory for processed files"),
    config: Optional[str] = Option(None, help="Configuration file path")
):
    """Process markdown files."""
    try:
        # Set up environment
        nova_config = setup_environment(Path(config) if config else None)
        
        # Override directories if provided
        if input_dir:
            nova_config.processing.input_dir = Path(input_dir)
        if output:
            nova_config.processing.phase_markdown_parse = Path(output)
            
        logger.info("starting_markdown_processing",
                   input_dir=str(nova_config.processing.input_dir),
                   output_dir=str(nova_config.processing.phase_markdown_parse))
        
        # Run markdown processing
        if not asyncio.run(process_markdown_files(nova_config)):
            sys.exit(1)
            
    except Exception as e:
        logger.error("markdown_processing_phase_failed", error=str(e))
        sys.exit(1)

@app.command()
def consolidate(
    input_dir: str = Option(None, "--input", help="Input directory containing processed markdown files"),
    output: str = Option(None, help="Output directory for consolidated files"),
    config: Optional[str] = Option(None, help="Configuration file path")
):
    """Consolidate processed markdown files."""
    try:
        # Set up environment
        nova_config = setup_environment(Path(config) if config else None)
        
        # Override directories if provided
        if input_dir:
            nova_config.processing.phase_markdown_parse = Path(input_dir)
        if output:
            nova_config.processing.phase_markdown_consolidate = Path(output)
            
        logger.info("starting_consolidation",
                   input_dir=str(nova_config.processing.phase_markdown_parse),
                   output_dir=str(nova_config.processing.phase_markdown_consolidate))
        
        # Run consolidation
        if not asyncio.run(consolidate_markdown(nova_config)):
            sys.exit(1)
            
    except Exception as e:
        logger.error("consolidation_phase_failed", error=str(e))
        sys.exit(1)

@app.command()
def generate_pdf(
    input_dir: str = Option(None, "--input", help="Input directory containing consolidated markdown files"),
    output: str = Option(None, "--output", help="Output directory for PDF files"),
    config: Optional[str] = Option(None, help="Configuration file path")
):
    """Generate PDF files from consolidated markdown."""
    try:
        # Set up environment
        nova_config = setup_environment(Path(config) if config else None)
        
        # Override directories if provided
        if input_dir:
            nova_config.processing.phase_markdown_consolidate = Path(input_dir)
        if output:
            nova_config.processing.phase_pdf_generate = Path(output)
            
        # Run PDF generation
        if not asyncio.run(generate_pdf_files(nova_config)):
            sys.exit(1)
            
    except Exception as e:
        logger.error("pdf_generation_phase_failed", error=str(e))
        sys.exit(1)

if __name__ == "__main__":
    app() 