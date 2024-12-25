"""Main entry point for the Nova document processor."""

import os
import sys
import time
import asyncio
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from nova.core.logging import get_logger
from nova.phases.parse.processor import MarkdownProcessor
from nova.phases.consolidate.processor import MarkdownConsolidateProcessor
from nova.phases.aggregate.processor import MarkdownAggregateProcessor
from nova.phases.split.processor import ThreeFileSplitProcessor
from nova.core.config import ProcessorConfig, HandlerConfig, PathConfig, PipelineConfig

logger = get_logger(__name__)
console = Console()

class Phase(Enum):
    """Pipeline processing phases."""
    SETUP = "Setup"
    PARSE = "Parse"
    CONSOLIDATE = "Consolidate"
    AGGREGATE = "Aggregate"
    SPLIT = "Split"
    CLEANUP = "Cleanup"

@dataclass
class ProcessingStats:
    """Statistics for pipeline processing."""
    files_processed: int = 0
    files_failed: int = 0
    errors: List[str] = field(default_factory=list)
    timings: Dict[str, float] = field(default_factory=dict)
    phase_timings: Dict[Phase, float] = field(default_factory=dict)

def format_time(seconds: float) -> str:
    """Format time in seconds to human readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds / 60)
    seconds = seconds % 60
    if minutes < 60:
        return f"{minutes}m {seconds:.1f}s"
    hours = int(minutes / 60)
    minutes = minutes % 60
    return f"{hours}h {minutes}m {seconds:.1f}s"

async def process_files(input_dir: Path, output_dir: Path, analyze_images: bool = False) -> ProcessingStats:
    """Process files in the input directory."""
    stats = ProcessingStats()
    start_time = time.time()
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            # SETUP phase
            setup_task = progress.add_task(f"[cyan]Phase: {Phase.SETUP.value}", total=2)
            phase_start = time.time()
            
            # Initialize processors
            progress.update(setup_task, advance=1, description=f"[cyan]Phase: {Phase.SETUP.value} (Initializing)")
            
            # Get phase directories
            parse_dir = Path(os.environ.get('NOVA_PHASE_MARKDOWN_PARSE'))
            consolidate_dir = Path(os.environ.get('NOVA_PHASE_MARKDOWN_CONSOLIDATE'))
            aggregate_dir = Path(os.environ.get('NOVA_PHASE_MARKDOWN_AGGREGATE'))
            split_dir = Path(os.environ.get('NOVA_PHASE_MARKDOWN_SPLIT'))
            
            # Create processor and pipeline configs
            processor_config = ProcessorConfig(
                name="markdown",
                description="Process markdown files",
                output_dir=str(parse_dir),
                processor="MarkdownProcessor",
                enabled=True,
                handlers=[
                    HandlerConfig(
                        type="MarkdownHandler",
                        base_handler="nova.phases.parse.handlers.markdown.MarkdownHandler",
                        image_processing=analyze_images
                    )
                ]
            )
            
            pipeline_config = PipelineConfig(
                paths=PathConfig(base_dir=str(input_dir)),
                phases=[processor_config],
                input_dir=str(input_dir),
                output_dir=str(output_dir),
                temp_dir=str(Path(os.environ.get('NOVA_TEMP_DIR', ''))),
                enabled=True
            )
            
            # Initialize processors
            markdown_processor = MarkdownProcessor(
                processor_config=ProcessorConfig(
                    name="markdown",
                    description="Process markdown files",
                    output_dir=str(parse_dir),
                    processor="MarkdownProcessor",
                    enabled=True,
                    components={
                        'handlers': {
                            'MarkdownHandler': {
                                'base_dir': str(input_dir),
                                'output_dir': str(parse_dir),
                                'input_dir': str(input_dir),
                                'analyze_images': analyze_images
                            }
                        }
                    },
                    handlers=[
                        HandlerConfig(
                            type="MarkdownHandler",
                            base_handler="nova.phases.parse.handlers.markdown.MarkdownHandler",
                            image_processing=analyze_images
                        )
                    ]
                ),
                pipeline_config=pipeline_config
            )
            consolidate_processor = MarkdownConsolidateProcessor(processor_config, pipeline_config)
            aggregate_processor = MarkdownAggregateProcessor(processor_config, pipeline_config)
            split_processor = ThreeFileSplitProcessor(processor_config, pipeline_config)
            
            # Set up processors
            if not await markdown_processor.setup():
                raise Exception("Failed to set up markdown processor")
            if not await consolidate_processor.setup():
                raise Exception("Failed to set up consolidate processor")
            if not await aggregate_processor.setup():
                raise Exception("Failed to set up aggregate processor")
            if not await split_processor.setup():
                raise Exception("Failed to set up split processor")
            
            # Count input files
            progress.update(setup_task, advance=1, description=f"[cyan]Phase: {Phase.SETUP.value} (Counting files)")
            input_files = list(input_dir.rglob("*"))
            markdown_files = [f for f in input_files if f.suffix.lower() == '.md']
            image_files = [f for f in input_files if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.heic', '.heif']]
            document_files = [f for f in input_files if f.suffix.lower() in ['.pdf', '.docx', '.xlsx', '.txt', '.csv']]
            
            stats.phase_timings[Phase.SETUP] = time.time() - phase_start
            progress.update(setup_task, completed=True)
            
            # PARSE phase
            parse_task = progress.add_task(
                f"[green]Phase: {Phase.PARSE.value}",
                total=len(markdown_files)
            )
            phase_start = time.time()
            
            # Process each markdown file
            for file in markdown_files:
                try:
                    context = {
                        'output_dir': parse_dir,
                        'attachments_dir': file.parent
                    }
                    result = await markdown_processor.process(file, context)
                    stats.files_processed += 1
                    if result:
                        progress.update(parse_task, advance=1)
                    else:
                        stats.files_failed += 1
                        stats.errors.append(f"Failed to process {file.name}")
                except Exception as e:
                    stats.files_failed += 1
                    stats.errors.append(f"Error processing {file.name}: {str(e)}")
                    logger.error(f"Failed to process {file.name}: {str(e)}")
            
            stats.phase_timings[Phase.PARSE] = time.time() - phase_start
            progress.update(parse_task, completed=True)
            
            # CONSOLIDATE phase
            consolidate_task = progress.add_task(
                f"[yellow]Phase: {Phase.CONSOLIDATE.value}",
                total=1
            )
            phase_start = time.time()
            
            try:
                await consolidate_processor.process()
                progress.update(consolidate_task, advance=1)
            except Exception as e:
                stats.errors.append(f"Error in consolidation phase: {str(e)}")
                logger.error(f"Failed to consolidate: {str(e)}")
            
            stats.phase_timings[Phase.CONSOLIDATE] = time.time() - phase_start
            progress.update(consolidate_task, completed=True)
            
            # AGGREGATE phase
            aggregate_task = progress.add_task(
                f"[blue]Phase: {Phase.AGGREGATE.value}",
                total=1
            )
            phase_start = time.time()
            
            try:
                await aggregate_processor.process()
                progress.update(aggregate_task, advance=1)
            except Exception as e:
                stats.errors.append(f"Error in aggregation phase: {str(e)}")
                logger.error(f"Failed to aggregate: {str(e)}")
            
            stats.phase_timings[Phase.AGGREGATE] = time.time() - phase_start
            progress.update(aggregate_task, completed=True)
            
            # SPLIT phase
            split_task = progress.add_task(
                f"[magenta]Phase: {Phase.SPLIT.value}",
                total=1
            )
            phase_start = time.time()
            
            try:
                await split_processor.process()
                progress.update(split_task, advance=1)
            except Exception as e:
                stats.errors.append(f"Error in split phase: {str(e)}")
                logger.error(f"Failed to split: {str(e)}")
            
            stats.phase_timings[Phase.SPLIT] = time.time() - phase_start
            progress.update(split_task, completed=True)
            
            # CLEANUP phase
            cleanup_task = progress.add_task(
                f"[red]Phase: {Phase.CLEANUP.value}",
                total=1
            )
            phase_start = time.time()
            
            # Perform cleanup operations here
            progress.update(cleanup_task, advance=1)
            
            stats.phase_timings[Phase.CLEANUP] = time.time() - phase_start
            progress.update(cleanup_task, completed=True)
    
    except Exception as e:
        stats.errors.append(f"Pipeline error: {str(e)}")
        logger.error(f"Pipeline failed: {str(e)}")
    
    stats.timings['total'] = time.time() - start_time
    return stats

def display_summary(stats: ProcessingStats, input_dir: Path) -> None:
    """Display processing summary."""
    table = Table(title="Processing Summary", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    
    # File counts
    input_files = list(input_dir.rglob("*"))
    markdown_files = [f for f in input_files if f.suffix.lower() == '.md']
    image_files = [f for f in input_files if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.heic', '.heif']]
    document_files = [f for f in input_files if f.suffix.lower() in ['.pdf', '.docx', '.xlsx', '.txt', '.csv']]
    
    table.add_row("Total Files", str(len(input_files)))
    table.add_row("Markdown Files", str(len(markdown_files)))
    table.add_row("Image Files", str(len(image_files)))
    table.add_row("Document Files", str(len(document_files)))
    table.add_row("Files Processed", str(stats.files_processed))
    table.add_row("Files Failed", str(stats.files_failed))
    
    # Phase timings
    table.add_section()
    for phase in Phase:
        if phase in stats.phase_timings:
            table.add_row(
                f"{phase.value} Time",
                format_time(stats.phase_timings[phase])
            )
    
    # Total time
    table.add_section()
    table.add_row(
        "Total Time",
        format_time(stats.timings['total']),
        style="bold green"
    )
    
    # Display summary
    console.print()
    console.print(Panel(table, title="Nova Pipeline Summary", border_style="green"))
    
    # Display errors if any
    if stats.errors:
        console.print()
        console.print(Panel(
            "\n".join(f"• {error}" for error in stats.errors),
            title="Errors",
            border_style="red"
        ))

async def main() -> int:
    """Main entry point."""
    try:
        # Get environment variables
        input_dir = Path(os.environ.get('NOVA_INPUT_DIR', ''))
        output_dir = Path(os.environ.get('NOVA_OUTPUT_DIR', ''))
        analyze_images = os.environ.get('NOVA_ANALYZE_IMAGES', '').lower() == 'true'
        
        if not input_dir.exists():
            console.print(f"[red]Error: Input directory {input_dir} does not exist[/red]")
            return 1
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Process files
        stats = await process_files(input_dir, output_dir, analyze_images)
        
        # Display summary
        display_summary(stats, input_dir)
        
        return 0 if stats.files_failed == 0 and not stats.errors else 1
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 