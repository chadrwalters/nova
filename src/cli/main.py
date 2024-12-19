"""Nova Document Processor CLI - Markdown Parse Phase"""

from pathlib import Path
from typing import Optional
from enum import Enum

import typer
from rich import print
from rich.table import Table
from rich.console import Console

from ..core.config import load_config
from ..core.validation import InputValidator
from ..core.logging import setup_logging
from ..core.state import StateManager
from ..processors.markdown_processor import MarkdownProcessor

app = typer.Typer(help="Nova Document Processor - Markdown Parse Phase")

class OutputFormat(str, Enum):
    """Output format options for state display."""
    SIMPLE = "simple"
    DETAILED = "detailed"
    JSON = "json"

def display_state(state_manager: StateManager, input_dir: Path, format: OutputFormat = OutputFormat.SIMPLE):
    """Display processing state information."""
    console = Console()
    
    if format == OutputFormat.JSON:
        # Get all state data and display as JSON
        import json
        states = {}
        for state_file in state_manager.state_dir.glob("*.state.json"):
            with open(state_file) as f:
                states[state_file.stem] = json.load(f)
        print(json.dumps(states, indent=2))
        return

    # Create table for display
    table = Table(title="Nova Processing State")
    table.add_column("File", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Last Processed", style="yellow")
    if format == OutputFormat.DETAILED:
        table.add_column("Hash", style="blue")
        table.add_column("Size", style="magenta")
        table.add_column("Attachments", style="red")

    # Process each markdown file
    for file_path in input_dir.rglob("*.md"):
        state = state_manager.load_state(file_path)
        needs_processing = state_manager.needs_processing(file_path)
        
        if format == OutputFormat.DETAILED:
            if state:
                table.add_row(
                    str(file_path.relative_to(input_dir)),
                    "Needs Update" if needs_processing else "Up to date",
                    state.file_info.last_processed,
                    state.file_info.hash[:8] + "...",
                    f"{state.file_info.size:,} bytes",
                    f"{len(state.attachments)} files"
                )
            else:
                table.add_row(
                    str(file_path.relative_to(input_dir)),
                    "Never processed",
                    "-",
                    "-",
                    f"{file_path.stat().st_size:,} bytes",
                    "-"
                )
        else:
            if state:
                table.add_row(
                    str(file_path.relative_to(input_dir)),
                    "Needs Update" if needs_processing else "Up to date",
                    state.file_info.last_processed
                )
            else:
                table.add_row(
                    str(file_path.relative_to(input_dir)),
                    "Never processed",
                    "-"
                )

    console.print(table)

@app.command()
def process(
    input_dir: Path = typer.Argument(
        ..., 
        exists=True, 
        file_okay=False, 
        dir_okay=True, 
        help="Input directory containing files to process"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force processing of all files, ignoring state"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show what would be processed without actually processing"
    ),
    show_state: Optional[OutputFormat] = typer.Option(
        None,
        "--show-state",
        "-s",
        help="Display current processing state"
    )
) -> None:
    """Process documents in the input directory."""
    try:
        # Load configuration
        config = load_config()
        setup_logging(config)
        
        # Initialize components
        validator = InputValidator(config)
        processor = MarkdownProcessor(config)
        
        # Show state if requested
        if show_state is not None:
            display_state(processor.state_manager, input_dir, show_state)
            return

        # Validate input directory
        validator.validate_directory(input_dir)
        
        # Clear state if force processing requested
        if force:
            print("[yellow]Force processing requested - clearing state[/yellow]")
            processor.state_manager.clear_state()
        
        # Handle dry run
        if dry_run:
            print("\n[cyan]Dry run - showing files that would be processed:[/cyan]")
            for file_path in input_dir.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in {'.md', '.markdown'}:
                    if processor.state_manager.needs_processing(file_path):
                        print(f"  Would process: {file_path.relative_to(input_dir)}")
                    else:
                        print(f"  Would skip: {file_path.relative_to(input_dir)}")
            return
        
        # Process directory
        processor.process_directory(input_dir)
        
    except Exception as e:
        print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(code=1)

@app.command()
def scan(
    input_dir: Path = typer.Argument(
        ..., 
        exists=True, 
        file_okay=False, 
        dir_okay=True, 
        help="Input directory to scan"
    ),
    processing_dir: Path = typer.Option(
        None,
        "--processing-dir",
        "-p",
        help="Processing directory to scan (defaults to NOVA_PHASE_MARKDOWN_PARSE)"
    )
):
    """Scan input and processing directories to show file structure."""
    if processing_dir is None:
        processing_dir = Path(os.getenv('NOVA_PHASE_MARKDOWN_PARSE'))

    console = Console()

    def print_tree(path: Path, prefix: str = "", is_last: bool = True, is_root: bool = False):
        if is_root:
            console.print(f"[bold blue]{path}[/]")
        else:
            marker = "└── " if is_last else "├── "
            console.print(f"{prefix}{marker}[green]{path.name}[/]")

        if path.is_dir():
            entries = sorted(path.iterdir())
            for i, entry in enumerate(entries):
                is_last_entry = i == len(entries) - 1
                new_prefix = prefix + ("    " if is_last else "│   ")
                print_tree(entry, new_prefix, is_last_entry)

    console.print("\n[bold]Input Directory Structure:[/]")
    print_tree(input_dir, is_root=True)

    if processing_dir.exists():
        console.print("\n[bold]Processing Directory Structure:[/]")
        print_tree(processing_dir, is_root=True)
    else:
        console.print("\n[bold red]Processing directory does not exist yet[/]")

if __name__ == "__main__":
    app() 