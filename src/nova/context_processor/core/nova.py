"""Nova document processor core."""

import logging
from pathlib import Path
from typing import Optional, Union

from ..config.manager import ConfigManager
from ..phases import (
    Phase,
    ParsePhase,
    DisassemblyPhase,
    SplitPhase,
    FinalizePhase,
)
from .metadata import (
    BaseMetadata,
    MetadataFactory,
    MetadataStore,
)
from .pipeline import NovaPipeline

logger = logging.getLogger(__name__)


class Nova:
    """Nova document processor."""

    def __init__(self, config: ConfigManager):
        """Initialize Nova processor.

        Args:
            config: Configuration manager
        """
        self.config = config
        self.pipeline = NovaPipeline(config)
        
        # Initialize metadata stores for each phase
        self.metadata_stores = {}
        for phase_name in ["parse", "disassembly", "split", "finalize"]:
            store_dir = config.base_dir / "_NovaProcessing" / "metadata" / phase_name
            self.metadata_stores[phase_name] = MetadataStore(store_dir=store_dir)

        # Initialize phases
        self.parse_phase = ParsePhase(config, self.metadata_stores["parse"])
        self.disassemble_phase = DisassemblyPhase(config, self.metadata_stores["disassembly"])
        self.split_phase = SplitPhase(config, self.metadata_stores["split"])
        self.finalize_phase = FinalizePhase(config, self.metadata_stores["finalize"])

        # Add phases in order
        self.phases = [
            self.parse_phase,
            self.disassemble_phase,
            self.split_phase,
            self.finalize_phase,
        ]

    async def process_file(self, file_path: Union[str, Path]) -> Optional[BaseMetadata]:
        """Process a file through the pipeline.

        Args:
            file_path: Path to file to process

        Returns:
            Optional[BaseMetadata]: Metadata if successful, None if failed
        """
        try:
            # Convert to Path
            file_path = Path(file_path)

            # Update total files count
            self.pipeline.stats["total_files"] += 1

            # Silently ignore .DS_Store files
            if file_path.name == ".DS_Store":
                self.pipeline.stats["skipped_files"] += 1
                return None

            # Process through each phase
            metadata = None
            for phase in self.phases:
                # Create phase output directory for processed files
                output_dir = self.config.base_dir / "_NovaProcessing" / "phases" / phase.name
                output_dir.mkdir(parents=True, exist_ok=True)

                # Process file in phase
                metadata = await phase.process_file(file_path, output_dir, metadata)
                if not metadata:
                    logger.error(f"Failed to process {file_path} in phase {phase.name}")
                    self.pipeline.stats["failed_files"] += 1
                    self.pipeline.stats["errors"].append({
                        "file": str(file_path),
                        "phase": phase.name,
                        "error": f"Failed to process in {phase.name} phase"
                    })
                    return None

            # Update success count
            self.pipeline.stats["processed_files"] += 1
            return metadata

        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {str(e)}")
            self.pipeline.stats["failed_files"] += 1
            self.pipeline.stats["errors"].append({
                "file": str(file_path),
                "error": str(e)
            })
            return None

    async def process_phase(self, phase: Phase) -> bool:
        """Process files in phase.

        Args:
            phase: Phase to process

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Process files
            return await phase.process()

        except Exception as e:
            logger.error(f"Failed to process phase {phase.__class__.__name__}: {e}")
            return False

    def finalize(self) -> None:
        """Run finalization steps."""
        try:
            # Run finalization
            self.pipeline.finalize()

        except Exception as e:
            logger.error(f"Finalization failed: {e}")
            raise
