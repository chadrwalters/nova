"""Nova pipeline implementation."""

import logging
import os
import time
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Set, Union
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn
import sys

from nova.config.manager import ConfigManager
from nova.config.settings import PipelineConfig
from nova.core.metadata import FileMetadata
from nova.phases.base import Phase
from nova.phases.parse import ParsePhase
from nova.phases.disassemble import DisassemblyPhase
from nova.phases.split import SplitPhase
from nova.phases.finalize import FinalizePhase
from nova.core.logging import print_summary
from nova.core.progress import ProgressTracker
from nova.utils.output_manager import OutputManager

logger = logging.getLogger(__name__)
console = Console()

class NovaPipeline:
    """Pipeline for processing files."""
    
    def __init__(self, config: ConfigManager):
        """Initialize pipeline.
        
        Args:
            config: Configuration manager
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.console = Console()
        
        # Initialize output manager
        self.output_manager = OutputManager(config)
        
        # Initialize state
        self.state = PipelineConfig.create_initial_state()
        self.error_messages: Dict[str, Dict[Path, str]] = {}
        
        # Initialize progress tracker
        self.progress_tracker = ProgressTracker()
        
        # Initialize phases
        self.phases = {
            "parse": ParsePhase(config, self),
            "disassemble": DisassemblyPhase(config, self),
            "split": SplitPhase(config, self),
            "finalize": FinalizePhase(config, self)
        }
        
        # Reset state after phases are initialized
        self.reset_state()
        
    def debug(self, message: str) -> None:
        """Print debug message if debug logging is enabled.
        
        Args:
            message: Message to print
        """
        if os.getenv('NOVA_LOG_LEVEL', '').upper() == 'DEBUG':
            self.logger.debug(message)
            
    def reset_state(self) -> None:
        """Reset pipeline state."""
        self.state = PipelineConfig.create_initial_state()
        
    def _add_failed_file(self, phase: str, file_path: Path, error_msg: str) -> None:
        """Add a file to the failed files set with its error message.
        
        Args:
            phase: Phase name
            file_path: Path to failed file
            error_msg: Error message
        """
        self.state[phase]['failed_files'].add(file_path)
        if phase not in self.error_messages:
            self.error_messages[phase] = {}
        self.error_messages[phase][file_path] = error_msg
        
    def _get_input_files(self, directory: Path) -> List[Path]:
        """Get list of input files from directory.
        
        Args:
            directory: Directory to scan for files
            
        Returns:
            List of file paths
        """
        files = []
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                # Skip hidden files and directories
                if not any(part.startswith('.') for part in file_path.parts):
                    files.append(file_path)
        return files
        
    def get_phase_output_dir(self, phase_name: str) -> Path:
        """Get output directory for a phase.
        
        Args:
            phase_name: Name of phase
            
        Returns:
            Path to output directory
        """
        output_dir = self.config.processing_dir / "phases" / phase_name
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
        
    async def process_directory(self, directory: Union[str, Path], phases: List[str] = None) -> bool:
        """Process all files in a directory.
        
        Args:
            directory: Directory to process
            phases: Optional list of phases to run. If None, runs all phases
            
        Returns:
            True if successful, False if failed
        """
        # Start timing
        start_time = time.time()
        
        try:
            # Convert directory to Path
            input_dir = Path(directory)
            
            # Initialize state
            self.state = {
                'parse': {'successful_files': set(), 'failed_files': set(), 'skipped_files': set()},
                'disassemble': {
                    'successful_files': set(), 
                    'failed_files': set(), 
                    'skipped_files': set(),
                    '_file_errors': {},
                    'stats': {
                        'total_processed': 0,
                        'total_sections': 0,
                        'summary_files': {
                            'created': 0,
                            'empty': 0,
                            'failed': 0
                        },
                        'raw_notes_files': {
                            'created': 0,
                            'empty': 0,
                            'failed': 0
                        },
                        'attachments': {
                            'copied': 0,
                            'failed': 0
                        }
                    }
                },
                'split': {'successful_files': set(), 'failed_files': set(), 'skipped_files': set()},
                'finalize': {'successful_files': set(), 'failed_files': set(), 'skipped_files': set()}
            }
            
            # Create progress display
            self.progress = Progress(
                TextColumn("[bold blue]{task.description:>12}"),
                BarColumn(bar_width=None),
                TextColumn("[progress.percentage]{task.completed}/{task.total}"),
                TaskProgressColumn(),
                expand=True,
                console=Console(file=sys.stderr, force_terminal=True)
            )
            
            # Process files through pipeline phases
            with self.progress:
                # Add tasks for each phase
                parse_task = self.progress.add_task("PARSE", total=0)
                disassemble_task = self.progress.add_task("DISASSEMBLE", total=0)
                split_task = self.progress.add_task("SPLIT", total=0)
                finalize_task = self.progress.add_task("FINALIZE", total=0)
                
                # Parse phase
                input_files = self._get_input_files(input_dir)
                self.progress.update(parse_task, total=len(input_files))
                parse_output_dir = self.get_phase_output_dir('parse')
                
                for file_path in input_files:
                    try:
                        metadata = await self.phases['parse'].process_file(file_path, parse_output_dir)
                        if metadata:
                            self.state['parse']['successful_files'].add(file_path)
                        else:
                            self.state['parse']['failed_files'].add(file_path)
                    except Exception as e:
                        self.logger.error(f"Error parsing {file_path}: {str(e)}")
                        self.logger.debug(traceback.format_exc())
                        self.state['parse']['failed_files'].add(file_path)
                    finally:
                        self.progress.advance(parse_task)
                
                # Disassemble phase
                disassemble_output_dir = self.get_phase_output_dir('disassemble')
                parsed_files = []
                for file_path in parse_output_dir.rglob('*.parsed.md'):
                    if file_path.is_file():
                        parsed_files.append(file_path)
                
                self.progress.update(disassemble_task, total=len(parsed_files))
                
                for file_path in parsed_files:
                    try:
                        metadata = await self.phases['disassemble'].process_file(file_path, disassemble_output_dir)
                        if metadata:
                            self.state['disassemble']['successful_files'].add(file_path)
                        else:
                            self.state['disassemble']['failed_files'].add(file_path)
                    except Exception as e:
                        self.logger.error(f"Error disassembling {file_path}: {str(e)}")
                        self.logger.debug(traceback.format_exc())
                        self.state['disassemble']['failed_files'].add(file_path)
                    finally:
                        self.progress.advance(disassemble_task)
                
                # Split phase
                disassemble_output_dir = self.get_phase_output_dir('disassemble')
                split_output_dir = self.get_phase_output_dir('split')
                
                # Get all summary files from disassemble phase
                summary_files = []
                for file_path in disassemble_output_dir.rglob('*.summary.md'):
                    if file_path.is_file():
                        summary_files.append(file_path)
                
                self.progress.update(split_task, total=len(summary_files))
                
                for file_path in summary_files:
                    try:
                        metadata = await self.phases['split'].process_file(file_path, split_output_dir)
                        if metadata:
                            self.state['split']['successful_files'].add(file_path)
                        else:
                            self.state['split']['failed_files'].add(file_path)
                    except Exception as e:
                        self.logger.error(f"Error splitting {file_path}: {str(e)}")
                        self.logger.debug(traceback.format_exc())
                        self.state['split']['failed_files'].add(file_path)
                    finally:
                        self.progress.advance(split_task)
                
                # Finalize phase
                finalize_output_dir = self.get_phase_output_dir('finalize')
                split_files = []
                for pattern in ['Summary.md', 'Raw Notes.md', 'Attachments.md']:
                    for file_path in split_output_dir.rglob(pattern):
                        if file_path.is_file():
                            split_files.append(file_path)
                
                self.progress.update(finalize_task, total=len(split_files))
                
                for file_path in split_files:
                    try:
                        metadata = await self.phases['finalize'].process_file(file_path, finalize_output_dir)
                        if metadata:
                            self.state['finalize']['successful_files'].add(file_path)
                        else:
                            self.state['finalize']['failed_files'].add(file_path)
                    except Exception as e:
                        self.logger.error(f"Error finalizing {file_path}: {str(e)}")
                        self.logger.debug(traceback.format_exc())
                        self.state['finalize']['failed_files'].add(file_path)
                    finally:
                        self.progress.advance(finalize_task)

            # Ensure progress bar is finished
            self.progress.refresh()
            self.progress.stop()
            
            # Clear screen after progress bar
            console = Console(file=sys.stderr, force_terminal=True)
            console.clear()
            
            # Show summary
            duration = time.time() - start_time
            self.show_summary(duration)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Pipeline error: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return False
            
    def show_summary(self, duration: float) -> None:
        """Show pipeline summary and statistics.
        
        Args:
            duration: Total processing duration in seconds
        """
        console = Console(file=sys.stderr, force_terminal=True)
        
        # Create main summary table
        table = Table(title="\n📊 Pipeline Summary", title_style="bold cyan", border_style="cyan")
        table.add_column("Phase", style="bold white")
        table.add_column("Total", justify="right")
        table.add_column("Successful", justify="right", style="green")
        table.add_column("Failed", justify="right", style="red")
        table.add_column("Skipped", justify="right", style="yellow")
        
        # Add rows for each phase
        total_successful = 0
        total_failed = 0
        total_skipped = 0
        
        for phase_name in ['parse', 'disassemble', 'split', 'finalize']:
            phase_state = self.state[phase_name]
            successful = len(phase_state['successful_files'])
            failed = len(phase_state['failed_files'])
            skipped = len(phase_state['skipped_files'])
            total = successful + failed + skipped
            
            table.add_row(
                phase_name.upper(),
                str(total),
                f"[green]{successful}[/green]" if successful > 0 else "0",
                f"[red]{failed}[/red]" if failed > 0 else "0",
                f"[yellow]{skipped}[/yellow]" if skipped > 0 else "0"
            )
            
            total_successful += successful
            total_failed += failed
            total_skipped += skipped
        
        # Add totals row
        table.add_row(
            "TOTAL",
            str(total_successful + total_failed + total_skipped),
            f"[green]{total_successful}[/green]" if total_successful > 0 else "0",
            f"[red]{total_failed}[/red]" if total_failed > 0 else "0",
            f"[yellow]{total_skipped}[/yellow]" if total_skipped > 0 else "0",
            style="bold"
        )
        
        # Print summary with spacing
        console.print("\n\n")
        console.print(table)
        console.print(f"\nTotal Duration: {duration:.2f}s", style="cyan")
        
        # Show phase-specific details
        if self.state['disassemble']['stats']['total_sections'] > 0:
            console.print("\n📑 Document Statistics:", style="bold cyan")
            stats = self.state['disassemble']['stats']
            doc_table = Table(show_header=False, box=None)
            doc_table.add_column("Metric", style="white")
            doc_table.add_column("Value", style="green")
            
            doc_table.add_row("Total Sections", str(stats['total_sections']))
            doc_table.add_row("Summary Files", f"{stats['summary_files']['created']} created, {stats['summary_files']['empty']} empty")
            doc_table.add_row("Raw Notes Files", f"{stats['raw_notes_files']['created']} created, {stats['raw_notes_files']['empty']} empty")
            doc_table.add_row("Attachments", f"{stats['attachments']['copied']} copied, {stats['attachments']['failed']} failed")
            
            console.print(doc_table)
        
        # Show failures if any
        if total_failed > 0:
            console.print("\n❌ Failed Files:", style="red bold")
            console.print("━" * 80, style="red")
            
            for phase_name in ['parse', 'disassemble', 'split', 'finalize']:
                phase_state = self.state[phase_name]
                if phase_state['failed_files']:
                    console.print(f"\n{phase_name.upper()} Phase:", style="red")
                    for file_path in phase_state['failed_files']:
                        console.print(f"• {Path(file_path).name}", style="red")
                        if phase_name in self.error_messages and file_path in self.error_messages[phase_name]:
                            console.print(f"  Error: {self.error_messages[phase_name][file_path]}", style="red")
                        console.print()
        
        console.print()  # Final newline for spacing 