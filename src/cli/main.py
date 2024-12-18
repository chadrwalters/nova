"""Nova Document Processor CLI - Markdown Parse Phase"""

from pathlib import Path
from typing import Optional

import typer
from rich import print

from ..core.config import load_config
from ..core.validation import InputValidator
from ..core.logging import setup_logging
from ..processors.markdown_processor import MarkdownProcessor

app = typer.Typer(help="Nova Document Processor - Markdown Parse Phase")

@app.command()
def process(
    input_path: Path = typer.Argument(
        ...,
        help="Input file or directory to process",
        exists=True,
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
) -> None:
    """Process markdown and office documents."""
    try:
        # Load configuration
        config = load_config(config_file)
        
        # Setup logging
        setup_logging(config.logging, verbose)
        
        # Validate first, then setup
        validator = InputValidator(config)
        validator.validate_environment()
        
        processor = MarkdownProcessor(config)
        processor._setup_directories()
        
        # Validate environment and input
        validator = InputValidator(config)
        validator.validate_environment()
        
        if input_path.is_file():
            validator.validate_file(input_path)
            processor.process_file(input_path)
        else:
            validator.validate_directory(input_path)
            processor.process_directory(input_path)
            
        print("[green]Processing completed successfully![/green]")
        
    except Exception as e:
        print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app() 