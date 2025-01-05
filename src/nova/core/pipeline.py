"""Nova pipeline implementation."""

import logging
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type, Union

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text

from nova.config.manager import ConfigManager
from nova.config.settings import PipelineConfig
from nova.core.logging import print_summary
from nova.core.metadata import FileMetadata
from nova.core.progress import ProgressTracker
from nova.phases.base import Phase
from nova.phases.disassemble import DisassemblyPhase
from nova.phases.finalize import FinalizePhase
from nova.phases.parse import ParsePhase
from nova.phases.split import SplitPhase
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

        # Initialize progress tracker
        self.progress_tracker = ProgressTracker()

        # Initialize progress display
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console,
            transient=False,
        )

        # Reset state
        self.reset_state()

    def debug(self, message: str) -> None:
        """Print debug message if debug logging is enabled.

        Args:
            message: Message to print
        """
        if getattr(self.config, "debug", False):
            self.logger.debug(message)

    def reset_state(self) -> None:
        """Reset pipeline state."""
        self.state = PipelineConfig.create_initial_state()

    def _add_failed_file(self, phase: str, file_path: Path, error_msg: str) -> None:
        """Add a file to the failed files list.

        Args:
            phase: Phase name
            file_path: Path to failed file
            error_msg: Error message
        """
        if phase not in self.state:
            self.state[phase] = {}
        if "failed_files" not in self.state[phase]:
            self.state[phase]["failed_files"] = set()
        self.state[phase]["failed_files"].add(file_path)
        if "_file_errors" not in self.state[phase]:
            self.state[phase]["_file_errors"] = {}
        self.state[phase]["_file_errors"][file_path] = error_msg

    def _get_input_files(self, directory: Path) -> List[Path]:
        """Get list of files to process from directory.

        Args:
            directory: Directory to scan

        Returns:
            List of file paths
        """
        files = []
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                files.append(file_path)
        return files

    def get_phase_output_dir(self, phase_name: str) -> Path:
        """Get output directory for a phase.

        Args:
            phase_name: Name of the phase

        Returns:
            Path to phase output directory
        """
        output_dir = self.config.processing_dir / "phases" / phase_name
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    async def process_directory(
        self, directory: Union[str, Path], phases: Optional[List[str]] = None
    ) -> bool:
        """Process all files in a directory through specified phases.

        Args:
            directory: Directory to process
            phases: List of phase names to run, or None for all phases

        Returns:
            True if successful, False if any errors occurred
        """
        # Convert directory to Path
        directory = Path(directory)

        # Get list of files to process
        input_files = self._get_input_files(directory)
        if not input_files:
            self.logger.warning(f"No files found in {directory}")
            return True

        # Start timing
        start_time = time.time()

        try:
            # Initialize phases
            available_phases: Dict[str, Phase] = {
                "parse": ParsePhase(self.config, self),
                "disassemble": DisassemblyPhase(self.config, self),
                "split": SplitPhase(self.config, self),
                "finalize": FinalizePhase(self.config, self),
            }

            # Determine which phases to run
            if phases is None:
                phases = list(available_phases.keys())
            else:
                # Validate requested phases
                for phase in phases:
                    if phase not in available_phases:
                        self.logger.error(f"Invalid phase: {phase}")
                        return False

            # Start progress display
            with self.progress:
                # Process each phase
                for phase_name in phases:
                    current_phase: Phase = available_phases[phase_name]
                    phase_output_dir = self.get_phase_output_dir(phase_name)

                    # Initialize state for this phase
                    if phase_name not in self.state:
                        self.state[phase_name] = {
                            "successful_files": set(),
                            "failed_files": set(),
                            "skipped_files": set(),
                            "unchanged_files": set(),
                            "_file_errors": {},
                        }

                    # Get input files for this phase
                    if phase_name == "parse":
                        # Parse phase uses original input files
                        phase_input_files = input_files
                    elif phase_name == "disassemble":
                        # Disassemble phase uses parsed markdown files
                        parse_dir = self.get_phase_output_dir("parse")
                        phase_input_files = [f for f in parse_dir.rglob("*.parsed.md")]
                    elif phase_name == "split":
                        # Split phase uses disassembled files
                        disassemble_dir = self.get_phase_output_dir("disassemble")
                        phase_input_files = [
                            f for f in disassemble_dir.rglob("*.summary.md")
                        ]
                        phase_input_files.extend(
                            [f for f in disassemble_dir.rglob("*.rawnotes.md")]
                        )
                    elif phase_name == "finalize":
                        # Finalize phase uses split files
                        split_dir = self.get_phase_output_dir("split")
                        phase_input_files = [f for f in split_dir.rglob("*")]
                    else:
                        # Unknown phase, use original input files
                        phase_input_files = input_files

                    # Create progress task for this phase
                    task_id = self.progress.add_task(
                        f"[cyan]{phase_name.upper()}[/cyan]",
                        total=len(phase_input_files),
                    )

                    # Process files for this phase
                    for file_path in phase_input_files:
                        try:
                            # Skip .DS_Store files silently without counting them
                            if str(file_path).endswith(".DS_Store"):
                                continue

                            metadata = await current_phase.process_file(
                                file_path, phase_output_dir
                            )
                            if metadata and metadata.processed:
                                self.state[phase_name]["successful_files"].add(
                                    file_path
                                )
                            else:
                                self.state[phase_name]["failed_files"].add(file_path)

                            # Update progress
                            self.progress.update(task_id, advance=1)

                        except Exception as e:
                            error_msg = f"{str(e)}\n{traceback.format_exc()}"
                            self.logger.error(
                                f"Error processing {file_path}: {error_msg}"
                            )
                            self._add_failed_file(phase_name, file_path, error_msg)
                            # Update progress even on error
                            self.progress.update(task_id, advance=1)

                    # Run phase finalization
                    try:
                        current_phase.finalize()
                    except Exception as e:
                        error_msg = f"Error in {phase_name} finalization: {str(e)}"
                        self.logger.error(error_msg)
                        self._add_failed_file(
                            phase_name, Path("finalization"), error_msg
                        )

            # Calculate duration and show summary
            duration = time.time() - start_time
            self.show_summary(duration)

            # Check for any failures
            for phase_name in phases:
                if self.state[phase_name]["failed_files"]:
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Pipeline error: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return False

    def show_summary(self, duration: float) -> None:
        """Show pipeline execution summary.

        Args:
            duration: Total execution time in seconds
        """
        # Create summary table
        table = Table(title="Pipeline Summary")
        table.add_column("Phase", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Files", justify="right")
        table.add_column("Details", justify="left")

        # Add rows for each phase
        for phase_name, phase_state in self.state.items():
            if isinstance(phase_state, dict):  # Skip non-dict state entries
                # Filter out metadata files
                successful_files = {
                    f
                    for f in phase_state.get("successful_files", set())
                    if not str(f).endswith(".metadata.json")
                }
                failed_files = {
                    f
                    for f in phase_state.get("failed_files", set())
                    if not str(f).endswith(".metadata.json")
                }
                skipped_files = {
                    f
                    for f in phase_state.get("skipped_files", set())
                    if not str(f).endswith(".metadata.json")
                }
                unchanged_files = {
                    f
                    for f in phase_state.get("unchanged_files", set())
                    if not str(f).endswith(".metadata.json")
                }

                successful = len(successful_files)
                failed = len(failed_files)
                skipped = len(skipped_files)
                unchanged = len(unchanged_files)

                status = "✓" if failed == 0 else "✗"
                style = "green" if failed == 0 else "red"

                details = []
                if successful > 0:
                    details.append(f"{successful} successful")
                if failed > 0:
                    details.append(f"{failed} failed")
                if skipped > 0:
                    details.append(f"{skipped} skipped")
                if unchanged > 0:
                    details.append(f"{unchanged} unchanged")

                # Add phase-specific details
                if phase_name == "disassemble" and "stats" in phase_state:
                    stats = phase_state["stats"]
                    summary_files = stats.get("summary_files", {}).get("created", 0)
                    raw_files = stats.get("raw_notes_files", {}).get("created", 0)
                    details.append(
                        f"→ {summary_files} summaries, {raw_files} raw notes"
                    )
                elif phase_name == "split":
                    details.append("(includes both summary and raw note files)")

                table.add_row(
                    phase_name.upper(),
                    Text(status, style=style),
                    str(successful + failed + skipped + unchanged),
                    ", ".join(details),
                )

        # Calculate total successful files
        total_successful = 0
        for phase_state in self.state.values():
            if isinstance(phase_state, dict):
                successful_files = phase_state.get("successful_files")
                if isinstance(successful_files, set):
                    total_successful += len(successful_files)

        # Add timing information
        table.add_row(
            "TIMING",
            "✓",
            f"{duration:.2f}s",
            f"Average: {duration/max(1, total_successful):.3f}s per file",
        )

        # Show the summary in a panel
        console.print(Panel(table, title="Pipeline Summary"))

        # Print any errors
        has_errors = False
        for phase_name, phase_state in self.state.items():
            if isinstance(phase_state, dict):
                errors = phase_state.get("_file_errors", {})
                if errors:
                    if not has_errors:
                        console.print("\nErrors:", style="red")
                        has_errors = True
                    console.print(f"\n{phase_name.upper()} Errors:", style="red")
                    for file_path, error_msg in errors.items():
                        console.print(f"  {file_path}:", style="yellow")
                        console.print(f"    {error_msg}", style="red")

    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats.

        Returns:
            List of supported file extensions.
        """
        formats = set()
        for phase_class in [ParsePhase, DisassemblyPhase, SplitPhase, FinalizePhase]:
            if hasattr(phase_class, "supported_formats"):
                formats.update(getattr(phase_class, "supported_formats"))
        return sorted(list(formats))
