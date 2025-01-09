"""Pipeline for processing documents."""

import logging
from pathlib import Path
from typing import List, Optional, Union, TYPE_CHECKING
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

from ..config.manager import ConfigManager
from ..handlers.base import ProcessingStatus, ProcessingResult
from ..phases import (
    Phase,
    ParsePhase,
    DisassemblyPhase,
    SplitPhase,
    FinalizePhase,
)
from .error_report import ErrorReport
from .metadata import MetadataStore

if TYPE_CHECKING:
    from ..core.metadata import BaseMetadata

logger = logging.getLogger(__name__)


class NovaPipeline:
    """Pipeline for processing documents."""

    def __init__(self, config: ConfigManager):
        """Initialize pipeline.

        Args:
            config: Configuration manager
        """
        self.config = config
        self.phases: List[Phase] = []
        self.stats = {
            "total_files": 0,
            "processed_files": 0,
            "failed_files": 0,
            "skipped_files": 0,
            "duplicate_files": 0,
            "errors": [],
        }
        self.error_report = ErrorReport(config.base_dir)

        # Initialize metadata stores for each phase
        self.metadata_stores = {}
        for phase_name in ["parse", "disassembly", "split", "finalize"]:
            store_dir = config.base_dir / "_NovaProcessing" / "metadata" / phase_name
            store_dir.mkdir(parents=True, exist_ok=True)
            self.metadata_stores[phase_name] = MetadataStore(store_dir=store_dir)

        # Initialize phases
        self.parse_phase = ParsePhase(config, self.metadata_stores["parse"])
        self.disassemble_phase = DisassemblyPhase(config, self.metadata_stores["disassembly"])
        self.split_phase = SplitPhase(config, self.metadata_stores["split"])
        self.finalize_phase = FinalizePhase(config, self.metadata_stores["finalize"])

        # Add phases in order
        self.phases.extend([
            self.parse_phase,
            self.disassemble_phase,
            self.split_phase,
            self.finalize_phase,
        ])

    async def process_file(
        self,
        file_path: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
    ) -> Optional["BaseMetadata"]:
        """Process a file through the pipeline.

        Args:
            file_path: Path to file to process
            output_dir: Optional output directory

        Returns:
            Optional[BaseMetadata]: Metadata if successful, None if failed
        """
        try:
            # Convert paths to Path objects
            file_path = Path(file_path)
            if output_dir:
                output_dir = Path(output_dir)
            else:
                output_dir = self.config.base_dir / "_NovaProcessing" / "phases"

            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)

            # Get base name without any extensions
            base_name = file_path.stem
            while "." in base_name:
                base_name = base_name.rsplit(".", 1)[0]

            # Check if this is a variant of an already processed file
            for phase in self.phases:
                phase_output_dir = output_dir / phase.name
                if phase_output_dir.exists():
                    existing_dirs = list(phase_output_dir.glob(f"{base_name}*"))
                    if existing_dirs:
                        # This is a variant, skip processing
                        logger.info(f"Skipping variant file: {file_path}")
                        self.stats["skipped_files"] += 1
                        return None

            # Update stats
            self.stats["total_files"] += 1

            # Process file through phases
            metadata = None
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
            ) as progress:
                # Create overall progress
                overall_task = progress.add_task(
                    f"[cyan]Processing {file_path.name}",
                    total=len(self.phases)
                )

                # Process through each phase
                for phase in self.phases:
                    phase_output_dir = output_dir / phase.name
                    phase_output_dir.mkdir(parents=True, exist_ok=True)

                    # Update progress description
                    progress.update(
                        overall_task,
                        description=f"[cyan]Processing {file_path.name} - {phase.name} phase"
                    )

                    # Process file in phase
                    metadata = await phase.process_file(file_path, phase_output_dir, metadata)
                    if not metadata:
                        logger.error(f"Failed to process {file_path} in phase {phase.name}")
                        self.stats["failed_files"] += 1
                        error_details = {
                            "file": str(file_path),
                            "phase": phase.name,
                            "error": "Phase processing failed"
                        }
                        self.stats["errors"].append(error_details)
                        return None

                    # Update progress
                    progress.advance(overall_task)

            # Update stats for successful processing
            self.stats["processed_files"] += 1
            return metadata

        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {str(e)}")
            self.stats["failed_files"] += 1
            error_details = {
                "file": str(file_path),
                "error": str(e)
            }
            self.stats["errors"].append(error_details)
            return None

    def finalize(self) -> None:
        """Run finalization steps for all phases and validate results."""
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
            ) as progress:
                # Create finalization task
                task = progress.add_task(
                    "[cyan]Running pipeline finalization",
                    total=len(self.phases)
                )

                # Finalize each phase
                for phase in self.phases:
                    progress.update(
                        task,
                        description=f"[cyan]Finalizing {phase.name} phase"
                    )
                    phase.finalize()
                    progress.advance(task)

            # Generate error report
            self.error_report.generate_report()

            # Log final statistics
            logger.info("Pipeline processing completed:")
            logger.info(f"- Total files: {self.stats['total_files']}")
            logger.info(f"- Processed files: {self.stats['processed_files']}")
            logger.info(f"- Failed files: {self.stats['failed_files']}")
            logger.info(f"- Skipped files: {self.stats['skipped_files']}")
            logger.info(f"- Duplicate files: {self.stats['duplicate_files']}")

            if self.stats["errors"]:
                logger.warning("Errors encountered during processing:")
                for error in self.stats["errors"]:
                    logger.warning(f"- {error['file']}: {error.get('error', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Pipeline finalization failed: {str(e)}")
            raise
