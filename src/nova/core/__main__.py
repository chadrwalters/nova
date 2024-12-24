"""Main entry point for Nova document processor."""

import asyncio
import os
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from .config.base import PipelineConfig, PathConfig, ProcessorConfig
from .pipeline.manager import PipelineManager
from .pipeline.phase import PhaseType
from .utils.logging import setup_logging
from .utils.paths import ensure_dir

console = Console()

def load_config() -> PipelineConfig:
    """Load pipeline configuration.
    
    Returns:
        Pipeline configuration
    """
    # Get base directory
    base_dir = os.getenv('NOVA_BASE_DIR')
    if not base_dir:
        raise click.ClickException("NOVA_BASE_DIR environment variable not set")
    
    # Create path config
    paths = PathConfig(
        base_dir=Path(base_dir),
        input_dir=Path(os.getenv('NOVA_INPUT_DIR', '')),
        output_dir=Path(os.getenv('NOVA_OUTPUT_DIR', '')),
        temp_dir=Path(os.getenv('NOVA_TEMP_DIR', ''))
    )
    
    # Create pipeline config
    config = PipelineConfig(paths=paths)
    
    # Set up processor configs
    for phase in PhaseType:
        phase_dir = paths.base_dir / f"phase_{phase.name.lower()}"
        
        # Create base processor config
        processor_config = ProcessorConfig(
            input_dir=paths.input_dir if phase == PhaseType.MARKDOWN_PARSE else phase_dir,
            output_dir=phase_dir
        )
        
        # Add phase-specific options
        if phase == PhaseType.MARKDOWN_PARSE:
            processor_config.options.update({
                'components': {
                    'markdown_processor': {
                        'config': {
                            'parser': 'markdown-it',
                            'typographer': True,
                            'plugins': [
                                'table',
                                'strikethrough',
                                'linkify',
                                'image'
                            ]
                        }
                    }
                }
            })
        elif phase == PhaseType.MARKDOWN_CONSOLIDATE:
            processor_config.options.update({
                'components': {
                    'consolidate_processor': {
                        'config': {
                            'group_by_root': True,
                            'handle_attachments': True,
                            'preserve_structure': True,
                            'attachment_markers': {
                                'start': '--==ATTACHMENT_BLOCK: {filename}==--',
                                'end': '--==ATTACHMENT_BLOCK_END==--'
                            }
                        }
                    }
                }
            })
        elif phase == PhaseType.MARKDOWN_AGGREGATE:
            processor_config.options.update({
                'components': {
                    'aggregate_processor': {
                        'config': {
                            'output_filename': 'all_merged_markdown.md',
                            'include_file_headers': True,
                            'add_separators': True
                        }
                    }
                }
            })
        elif phase == PhaseType.MARKDOWN_SPLIT_THREEFILES:
            processor_config.options.update({
                'components': {
                    'three_file_split_processor': {
                        'config': {
                            'output_files': {
                                'summary': 'summary.md',
                                'raw_notes': 'raw_notes.md',
                                'attachments': 'attachments.md'
                            },
                            'section_markers': {
                                'summary': '--==SUMMARY==--',
                                'raw_notes': '--==RAW_NOTES==--',
                                'attachments': '--==ATTACHMENTS==--'
                            },
                            'attachment_markers': {
                                'start': '--==ATTACHMENT_BLOCK: {filename}==--',
                                'end': '--==ATTACHMENT_BLOCK_END==--'
                            },
                            'content_type_rules': {
                                'summary': [
                                    'Contains high-level overviews',
                                    'Contains key insights and decisions',
                                    'Contains structured content'
                                ],
                                'raw_notes': [
                                    'Contains detailed notes and logs',
                                    'Contains chronological entries',
                                    'Contains unstructured content'
                                ],
                                'attachments': [
                                    'Contains file references',
                                    'Contains embedded content',
                                    'Contains metadata'
                                ]
                            },
                            'content_preservation': {
                                'validate_input_size': True,
                                'validate_output_size': True,
                                'track_content_markers': True,
                                'verify_section_integrity': True
                            },
                            'cross_linking': True,
                            'preserve_headers': True
                        }
                    }
                }
            })
        
        config.set_processor_config(phase.name, processor_config)
    
    return config

def setup_directories(config: PipelineConfig) -> None:
    """Set up required directories.
    
    Args:
        config: Pipeline configuration
    """
    # Create base directories
    ensure_dir(config.paths.base_dir)
    ensure_dir(config.paths.input_dir)
    ensure_dir(config.paths.output_dir)
    ensure_dir(config.paths.temp_dir)
    
    # Create phase directories
    for phase in PhaseType:
        phase_dir = config.paths.base_dir / f"phase_{phase.name.lower()}"
        ensure_dir(phase_dir)

@click.group()
def cli():
    """Nova document processor CLI."""
    pass

@cli.command()
@click.option('--start-phase', type=click.Choice([p.name for p in PhaseType]))
@click.option('--end-phase', type=click.Choice([p.name for p in PhaseType]))
@click.option('--force', is_flag=True, help="Force processing")
@click.option('--dry-run', is_flag=True, help="Show what would be done")
def process(
    start_phase: Optional[str] = None,
    end_phase: Optional[str] = None,
    force: bool = False,
    dry_run: bool = False
):
    """Process documents through pipeline."""
    try:
        # Set up logging
        setup_logging()
        
        # Load config
        config = load_config()
        
        # Set up directories
        setup_directories(config)
        
        # Create pipeline manager
        manager = PipelineManager(config)
        
        # Get phase range
        start = PhaseType[start_phase] if start_phase else None
        end = PhaseType[end_phase] if end_phase else None
        
        # Show plan if dry run
        if dry_run:
            phases = manager._get_phase_range(start, end)
            console.print("\n[bold]Pipeline plan:[/bold]")
            for phase in phases:
                console.print(f"  • {phase.name}")
            return
        
        # Run pipeline
        console.print("\n[bold]Starting pipeline...[/bold]")
        success = manager.run_pipeline(
            input_path=str(config.paths.input_dir),
            output_path=str(config.paths.output_dir),
            start_phase=start,
            end_phase=end,
            options={'force': force}
        )
        
        # Show result
        if success:
            console.print("\n[bold green]Pipeline completed successfully[/bold green]")
        else:
            console.print("\n[bold red]Pipeline failed[/bold red]")
            raise click.ClickException("Pipeline failed")
            
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        raise click.ClickException(str(e))

@cli.command()
def show_state():
    """Show current pipeline state."""
    try:
        # Set up logging
        setup_logging()
        
        # Load config
        config = load_config()
        
        # Create pipeline manager
        manager = PipelineManager(config)
        
        # Get state
        state = manager.get_state()
        
        # Show state
        console.print("\n[bold]Pipeline state:[/bold]")
        for phase, phase_state in state.items():
            console.print(f"\n[bold]{phase}:[/bold]")
            for key, value in phase_state.items():
                console.print(f"  {key}: {value}")
            
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        raise click.ClickException(str(e))

@cli.command()
def reset_state():
    """Reset pipeline state."""
    try:
        # Set up logging
        setup_logging()
        
        # Load config
        config = load_config()
        
        # Create pipeline manager
        manager = PipelineManager(config)
        
        # Reset state
        manager.reset_state()
        
        console.print("\n[bold green]Pipeline state reset[/bold green]")
            
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        raise click.ClickException(str(e))

@cli.command()
def scan():
    """Scan input directory."""
    try:
        # Set up logging
        setup_logging()
        
        # Load config
        config = load_config()
        
        # Show directory structure
        console.print("\n[bold]Directory structure:[/bold]")
        
        def print_tree(path: Path, prefix: str = ""):
            """Print directory tree."""
            # Print current path
            name = path.name or str(path)
            console.print(f"{prefix}{'└── ' if prefix else ''}{name}")
            
            # Print children
            if path.is_dir():
                prefix = prefix + ("    " if prefix else "")
                for child in sorted(path.iterdir()):
                    print_tree(child, prefix)
        
        print_tree(config.paths.base_dir)
            
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        raise click.ClickException(str(e))

if __name__ == "__main__":
    cli() 