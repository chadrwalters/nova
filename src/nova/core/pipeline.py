"""Nova pipeline implementation."""

import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Union
import traceback
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn

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
                expand=True
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
                self.progress.update(finalize_task, total=3)  # 3 steps: validate, copy, summarize
                
                try:
                    # Run finalize phase
                    self.phases['finalize'].finalize()
                    self.progress.advance(finalize_task, 3)
                    
                except Exception as e:
                    self.logger.error(f"Error in finalize: {str(e)}")
                    self.logger.error(traceback.format_exc())
                    self.state['finalize']['failed_files'].add('finalize')
                    self.state['finalize'].update({
                        'completed': True,
                        'success': False
                    })
                    return False
                    
                # Only mark as complete if successful
                self.state['finalize'].update({
                    'completed': True,
                    'success': True
                })
                
                return True
                
            # Wait for progress to complete
            self.progress.refresh()
            
            # Show final summary
            self.show_summary()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Pipeline error: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return False
            
    def show_summary(self):
        """Show pipeline summary and statistics."""
        # Create console for rich output
        console = Console()
        
        # Create summary table
        table = Table(title="Pipeline Summary", show_header=True, header_style="bold cyan", box=None)
        table.add_column("Phase", style="cyan")
        table.add_column("Total", justify="right")
        table.add_column("Completed", justify="right", style="green")
        table.add_column("Failed", justify="right", style="red")
        table.add_column("Skipped", justify="right", style="yellow")
        table.add_column("Duration", justify="right")
        
        total_files = 0
        total_completed = 0
        total_failed = 0
        total_skipped = 0
        
        # Add rows for each phase
        for phase_name, phase_state in self.state.items():
            if phase_name in ['parse', 'disassemble', 'split', 'finalize']:
                completed = len(phase_state.get('successful_files', set()))
                failed = len(phase_state.get('failed_files', set()))
                skipped = len(phase_state.get('skipped_files', set()))
                phase_total = completed + failed + skipped
                duration = phase_state.get('duration', 0)
                duration_str = f"{duration:.1f}s" if duration else "-"
                
                table.add_row(
                    phase_name.upper(),
                    str(phase_total),
                    str(completed),
                    str(failed),
                    str(skipped),
                    duration_str
                )
                
                total_files += phase_total
                total_completed += completed
                total_failed += failed
                total_skipped += skipped
        
        # Add totals row
        total_duration = sum(phase_state.get('duration', 0) for phase_state in self.state.values())
        table.add_row(
            "TOTAL",
            str(total_files),
            str(total_completed),
            str(total_failed),
            str(total_skipped),
            f"{total_duration:.1f}s",
            style="bold"
        )
        
        # Print summary table
        console.print("\nPipeline Summary:", style="yellow bold")
        console.print(table)
        
        # Print detailed phase statistics
        console.print("\nPhase Statistics:", style="yellow bold")
        
        # Parse phase stats - File type table
        if 'parse' in self.state:
            parse_state = self.state['parse']
            file_types = {}
            success_types = {}
            failed_types = {}
            
            # Count successful and failed files by type
            for file_path in parse_state.get('successful_files', set()):
                file_type = file_path.suffix.lower()
                success_types[file_type] = success_types.get(file_type, 0) + 1
                file_types[file_type] = True
                
            for file_path in parse_state.get('failed_files', set()):
                file_type = file_path.suffix.lower()
                failed_types[file_type] = failed_types.get(file_type, 0) + 1
                file_types[file_type] = True
            
            if file_types:
                # Create file types table
                types_table = Table(show_header=True, header_style="bold cyan", title="File Types", box=None)
                types_table.add_column("Status", style="cyan")
                
                # Add columns for each file type
                file_type_list = sorted(file_types.keys())
                for file_type in file_type_list:
                    types_table.add_column(file_type, justify="right")
                
                # Add success row
                success_row = ["Success"]
                for file_type in file_type_list:
                    success_row.append(str(success_types.get(file_type, 0)))
                types_table.add_row(*success_row, style="green")
                
                # Add failed row if there are any failures
                if failed_types:
                    failed_row = ["Failed"]
                    for file_type in file_type_list:
                        failed_row.append(str(failed_types.get(file_type, 0)))
                    types_table.add_row(*failed_row, style="red")
                
                console.print("\nParse phase:", style="yellow")
                console.print(types_table)
        
        # Disassemble phase stats
        if 'disassemble' in self.state:
            disassemble_state = self.state['disassemble']
            total_sections = disassemble_state.get('stats', {}).get('total_sections', 0)
            total_attachments = disassemble_state.get('stats', {}).get('total_attachments', 0)
            
            # Create disassemble stats table
            disassemble_table = Table(show_header=True, header_style="bold cyan", title="Disassemble Results", box=None)
            disassemble_table.add_column("Metric", style="cyan")
            disassemble_table.add_column("Count", justify="right")
            
            disassemble_table.add_row("Total Sections", str(total_sections))
            disassemble_table.add_row("Total Attachments", str(total_attachments))
            
            console.print("\nDisassemble phase:", style="yellow")
            console.print(disassemble_table)
        
        # Split phase stats
        if 'split' in self.state:
            split_state = self.state['split']
            section_stats = {}
            
            # Aggregate section stats from all files
            for file_sections in split_state.get('sections', {}).values():
                for section in file_sections:
                    section_type = section.get('type', 'unknown')
                    section_stats[section_type] = section_stats.get(section_type, 0) + 1
            
            if section_stats:
                # Create section types table
                section_table = Table(show_header=True, header_style="bold cyan", title="Section Types", box=None)
                section_table.add_column("Type", style="cyan")
                section_table.add_column("Count", justify="right")
                
                for section_type, count in sorted(section_stats.items()):
                    section_table.add_row(section_type, str(count))
                
                console.print("\nSplit phase:", style="yellow")
                console.print(section_table)
        
        # Show failures if any
        if total_failed > 0:
            console.print(f"\nFailed files: {total_failed}", style="red bold")
            for phase_name, phase_state in self.state.items():
                failed_files = phase_state.get('failed_files', set())
                if failed_files:
                    console.print(f"\n{phase_name.upper()} phase failures:", style="red")
                    for file_path in failed_files:
                        console.print(f"  • {file_path}", style="red")
        else:
            console.print("\nAll files processed successfully!", style="green bold") 