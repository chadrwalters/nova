"""Finalize phase module."""

import logging
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
import traceback

from nova.core.metadata import FileMetadata
from nova.phases.base import Phase
from rich.console import Console
from rich.table import Table

class FinalizePhase(Phase):
    """Final phase that checks overall pipeline success and copies results if successful."""
    
    def __init__(self, pipeline):
        """Initialize finalize phase.
        
        Args:
            pipeline: Pipeline instance this phase belongs to
        """
        super().__init__(pipeline)
        self.logger = logging.getLogger(__name__)
        self.name = "finalize"
        
        # Initialize state
        self.pipeline.state["finalize"] = {
            'successful_files': set(),
            'failed_files': set(),
            'skipped_files': set(),
            'unchanged_files': set(),
            'reprocessed_files': set()
        }
        
    async def process_file(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: Optional[FileMetadata] = None
    ) -> Optional[FileMetadata]:
        """Process a single file by copying it to the final output directory.
        
        Args:
            file_path: Path to file to process
            output_dir: Directory to write output files to
            metadata: Optional metadata from previous phase
            
        Returns:
            Metadata about processed file, or None if file was skipped
        """
        try:
            self.logger.debug(f"Finalize phase processing file: {file_path}")
            
            # Initialize metadata if not provided
            if metadata is None:
                metadata = FileMetadata(file_path)
            
            # Get the split phase directory
            split_dir = self.pipeline.config.processing_dir / "phases" / "split"
            self.logger.debug(f"Split directory: {split_dir}")
            
            # Look for the main files in the split directory
            main_files = ["Summary.md", "Raw Notes.md", "Attachments.md"]
            for main_file in main_files:
                main_file_path = split_dir / main_file
                if main_file_path.exists():
                    # Copy to the output directory
                    final_output_path = self.pipeline.config.output_dir / main_file
                    self.logger.debug(f"Copying {main_file_path} to {final_output_path}")
                    
                    # Create output directory if it doesn't exist
                    final_output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy the file
                    shutil.copy2(main_file_path, final_output_path)
                    self.logger.debug(f"Successfully copied {main_file} to {final_output_path}")
                    
                    # Update metadata
                    metadata.processed = True
                    metadata.add_output_file(final_output_path)
                    self.pipeline.state['finalize']['successful_files'].add(main_file_path)
                else:
                    self.logger.debug(f"Main file not found: {main_file_path}")
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to copy file {file_path}: {str(e)}")
            self.logger.error(traceback.format_exc())
            if metadata:
                metadata.add_error("FinalizePhase", str(e))
                metadata.processed = False
                self.pipeline.state['finalize']['failed_files'].add(file_path)
                return metadata
            return None
            
    def print_final_summary(self) -> None:
        """Print a consolidated summary of all phases in a table format."""
        console = Console()
        table = Table(title="Nova Pipeline Summary")
        
        # Add columns
        table.add_column("Phase", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Processed", justify="right")
        table.add_column("Failed", justify="right", style="red")
        table.add_column("Skipped", justify="right", style="yellow")
        table.add_column("Unchanged", justify="right", style="blue")
        
        # Add rows for each phase
        for phase_name, phase_state in self.pipeline.state.items():
            # Calculate status
            has_failures = bool(phase_state.get('failed_files', set()))
            status = "[red]Failed[/red]" if has_failures else "[green]Success[/green]"
            
            # Count files
            successful = len(phase_state.get('successful_files', set()))
            failed = len(phase_state.get('failed_files', set()))
            skipped = len(phase_state.get('skipped_files', set()))
            unchanged = len(phase_state.get('unchanged_files', set()))
            
            # For parse phase, count unchanged files as processed
            if phase_name == "parse":
                processed = successful + unchanged
            else:
                processed = successful
            
            table.add_row(
                phase_name.capitalize(),
                status,
                str(processed),
                str(failed),
                str(skipped),
                str(unchanged)
            )
        
        # Print the table
        console.print(table)
        
    def check_pipeline_success(self) -> bool:
        """Check if all previous phases completed successfully.
        
        Returns:
            bool: True if all phases succeeded, False otherwise
        """
        for phase_name, phase_state in self.pipeline.state.items():
            if phase_name == "finalize":
                continue
            if phase_state.get('failed_files', set()):
                return False
        return True 