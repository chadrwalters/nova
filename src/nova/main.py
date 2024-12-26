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
from nova.core.file_info_provider import FileInfoProvider

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

class ProcessingError(Exception):
    """Error raised when processing files fails."""
    pass

@dataclass
class ProcessingStats:
    """Statistics for pipeline processing."""
    total_files: int = 0
    markdown_files: int = 0
    image_files: int = 0
    document_files: int = 0
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

async def process_files(input_path: Path, output_path: Path, analyze_images: bool = False) -> ProcessingStats:
    """Process markdown files.
    
    Args:
        input_path: Path to input directory
        output_path: Path to output directory
        analyze_images: Whether to analyze images
        
    Returns:
        ProcessingStats containing processing results
    """
    try:
        start_time = time.time()
        
        # Initialize processors
        pipeline_config = PipelineConfig(
            paths={
                'base_dir': str(Path(os.path.expandvars(os.environ.get('NOVA_BASE_DIR', '')))),
                'input_dir': str(Path(os.path.expandvars(os.environ.get('NOVA_INPUT_DIR', '')))),
                'output_dir': str(Path(os.path.expandvars(os.environ.get('NOVA_OUTPUT_DIR', ''))))
            },
            phases=[
                ProcessorConfig(
                    name='MARKDOWN_PARSE',
                    description='Parse and process markdown files',
                    output_dir=str(Path(os.path.expandvars(os.environ.get('NOVA_PHASE_MARKDOWN_PARSE', '')))),
                    processor='MarkdownProcessor',
                    options={
                        'analyze_images': analyze_images
                    }
                ),
                ProcessorConfig(
                    name='MARKDOWN_CONSOLIDATE',
                    description='Consolidate markdown files',
                    output_dir=str(Path(os.path.expandvars(os.environ.get('NOVA_PHASE_MARKDOWN_CONSOLIDATE', '')))),
                    processor='MarkdownConsolidateProcessor'
                ),
                ProcessorConfig(
                    name='MARKDOWN_AGGREGATE',
                    description='Aggregate markdown files',
                    output_dir=str(Path(os.path.expandvars(os.environ.get('NOVA_PHASE_MARKDOWN_AGGREGATE', '')))),
                    processor='MarkdownAggregateProcessor'
                ),
                ProcessorConfig(
                    name='MARKDOWN_SPLIT',
                    description='Split aggregated markdown into summary, raw notes, and attachments',
                    output_dir=str(Path(os.path.expandvars(os.environ.get('NOVA_PHASE_MARKDOWN_SPLIT', '')))),
                    processor='ThreeFileSplitProcessor'
                )
            ]
        )
        
        markdown_processor = MarkdownProcessor(
            processor_config=pipeline_config.phases[0],
            pipeline_config=pipeline_config
        )
        
        consolidate_processor = MarkdownConsolidateProcessor(
            processor_config=pipeline_config.phases[1],
            pipeline_config=pipeline_config
        )
        
        aggregate_processor = MarkdownAggregateProcessor(
            processor_config=pipeline_config.phases[2],
            pipeline_config=pipeline_config
        )
        
        split_processor = ThreeFileSplitProcessor(
            processor_config=pipeline_config.phases[3],
            pipeline_config=pipeline_config
        )
        
        # Process files
        markdown_files = list(input_path.rglob('*.md'))
        logger.info(f"Found {len(markdown_files)} markdown files in {input_path}")
        
        failed_files = 0
        errors = []
        for file in markdown_files:
            try:
                await markdown_processor.process(file)
            except Exception as e:
                error_msg = f"Failed to process {file}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                failed_files += 1
                
        await consolidate_processor.process()
        await aggregate_processor.process()
        await split_processor.process()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        return ProcessingStats(
            total_files=len(list(input_path.rglob('*'))),
            markdown_files=len(markdown_files),
            image_files=len(list(input_path.rglob('*.jpg')) + list(input_path.rglob('*.jpeg')) + list(input_path.rglob('*.png')) + list(input_path.rglob('*.gif'))),
            document_files=len(list(input_path.rglob('*.pdf')) + list(input_path.rglob('*.docx')) + list(input_path.rglob('*.xlsx'))),
            files_processed=len(markdown_files),
            files_failed=failed_files,
            errors=errors,
            timings={'total': total_time},
            phase_timings={}
        )
        
    except Exception as e:
        logger.error(f"Failed to process files: {e}")
        raise ProcessingError(f"Failed to process files: {e}")

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
        # Get directories from environment
        parse_dir = Path(os.path.expandvars(os.environ.get('NOVA_PHASE_MARKDOWN_PARSE', '')))
        consolidate_dir = Path(os.path.expandvars(os.environ.get('NOVA_PHASE_MARKDOWN_CONSOLIDATE', '')))
        aggregate_dir = Path(os.path.expandvars(os.environ.get('NOVA_PHASE_MARKDOWN_AGGREGATE', '')))
        split_dir = Path(os.path.expandvars(os.environ.get('NOVA_PHASE_MARKDOWN_SPLIT', '')))
        
        # Create pipeline configuration
        config = PipelineConfig(
            phases=[
                PhaseConfig(
                    name='parse',
                    description='Parse markdown files',
                    processor='MarkdownParseProcessor',
                    input_dir=str(Path(os.path.expandvars(os.environ.get('NOVA_INPUT_DIR', '')))),
                    output_dir=str(parse_dir),
                    temp_dir=str(Path(os.path.expandvars(os.environ.get('NOVA_TEMP_DIR', '')))),
                    analyze_images=os.environ.get('NOVA_ANALYZE_IMAGES', '').lower() == 'true'
                ),
                PhaseConfig(
                    name='consolidate',
                    description='Consolidate markdown files',
                    processor='MarkdownConsolidateProcessor',
                    input_dir=str(parse_dir),
                    output_dir=str(consolidate_dir)
                ),
                PhaseConfig(
                    name='aggregate',
                    description='Aggregate markdown files',
                    processor='MarkdownAggregateProcessor',
                    input_dir=str(consolidate_dir),
                    output_dir=str(aggregate_dir)
                ),
                PhaseConfig(
                    name='split',
                    description='Split markdown files',
                    processor='MarkdownSplitProcessor',
                    input_dir=str(aggregate_dir),
                    output_dir=str(split_dir)
                )
            ]
        )
        
        # Create and run pipeline
        pipeline = Pipeline(config)
        pipeline.run()
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        raise

def get_env_path(key: str, default: str = '') -> Path:
    """Get environment variable as Path with proper expansion."""
    value = os.environ.get(key, default)
    expanded = os.path.expandvars(value)
    return Path(expanded)

def get_pipeline_config() -> Dict[str, Any]:
    """Get pipeline configuration."""
    return {
        'phases': {
            'MARKDOWN_PARSE': {
                'description': 'Parse and process markdown files with embedded content',
                'output_dir': get_env_path('NOVA_PHASE_MARKDOWN_PARSE'),
                'processor': 'MarkdownProcessor',
                'components': {
                    'markdown_processor': {
                        'parser': 'markitdown==0.0.1a3',
                        'config': {
                            'document_conversion': True,
                            'image_processing': True,
                            'metadata_preservation': True
                        }
                    }
                }
            },
            'MARKDOWN_CONSOLIDATE': {
                'description': 'Consolidate markdown files with their attachments',
                'output_dir': get_env_path('NOVA_PHASE_MARKDOWN_CONSOLIDATE'),
                'processor': 'MarkdownConsolidateProcessor',
                'components': {
                    'consolidate_processor': {
                        'config': {
                            'group_by_root': True,
                            'handle_attachments': True,
                            'preserve_structure': True
                        }
                    }
                }
            },
            'MARKDOWN_AGGREGATE': {
                'description': 'Aggregate all consolidated markdown files into a single file',
                'output_dir': get_env_path('NOVA_PHASE_MARKDOWN_AGGREGATE'),
                'processor': 'MarkdownAggregateProcessor',
                'components': {
                    'aggregate_processor': {
                        'config': {
                            'output_filename': 'all_merged_markdown.md',
                            'include_file_headers': True,
                            'add_separators': True
                        }
                    }
                }
            },
            'MARKDOWN_SPLIT_THREEFILES': {
                'description': 'Split aggregated markdown into summary, raw notes, and attachments',
                'output_dir': get_env_path('NOVA_PHASE_MARKDOWN_SPLIT'),
                'processor': 'ThreeFileSplitProcessor',
                'components': {
                    'split_processor': {
                        'config': {
                            'output_files': {
                                'summary': 'summary.md',
                                'raw_notes': 'raw_notes.md',
                                'attachments': 'attachments.md'
                            }
                        }
                    }
                }
            }
        }
    }

def get_base_config() -> Dict[str, Any]:
    """Get base configuration."""
    return {
        'base_dir': get_env_path('NOVA_BASE_DIR'),
        'input_dir': get_env_path('NOVA_INPUT_DIR'),
        'output_dir': get_env_path('NOVA_OUTPUT_DIR'),
        'processing_dir': get_env_path('NOVA_PROCESSING_DIR'),
        'temp_dir': get_env_path('NOVA_TEMP_DIR'),
        'state_dir': get_env_path('NOVA_STATE_DIR'),
        'image_dirs': {
            'original': get_env_path('NOVA_ORIGINAL_IMAGES_DIR'),
            'processed': get_env_path('NOVA_PROCESSED_IMAGES_DIR'),
            'metadata': get_env_path('NOVA_IMAGE_METADATA_DIR'),
            'cache': get_env_path('NOVA_IMAGE_CACHE_DIR'),
            'temp': get_env_path('NOVA_IMAGE_TEMP_DIR')
        },
        'office_dirs': {
            'assets': get_env_path('NOVA_OFFICE_ASSETS_DIR'),
            'temp': get_env_path('NOVA_OFFICE_TEMP_DIR')
        }
    }

if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 