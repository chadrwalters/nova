"""Parse phase implementation."""

# Standard library
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Union
import re

# Internal imports
from ..config.manager import ConfigManager
from ..core.metadata import FileMetadata, DocumentMetadata
from ..handlers.base import BaseHandler, ProcessingStatus
from ..handlers.registry import HandlerRegistry
from ..phases.base import Phase

if TYPE_CHECKING:
    from ..core.pipeline import NovaPipeline

logger = logging.getLogger(__name__)


class ParsePhase(Phase):
    """Parse phase implementation."""

    def __init__(self, config: ConfigManager, pipeline: "NovaPipeline") -> None:
        """Initialize phase.

        Args:
            config: Nova configuration manager
            pipeline: Pipeline instance
        """
        super().__init__("parse", config, pipeline)
        self.handler_registry = HandlerRegistry(config, pipeline)
        self.stats: Dict[str, Dict] = {}

    def _get_handler(self, file_path: Path) -> Optional[BaseHandler]:
        """Get appropriate handler for file type.

        Args:
            file_path: Path to file

        Returns:
            Handler instance or None if no handler available
        """
        return self.handler_registry.get_handler(file_path)

    async def process_file(
        self, file_path: Union[str, Path], output_dir: Union[str, Path]
    ) -> Optional[DocumentMetadata]:
        """Process a single file.

        Args:
            file_path: Path to file to process
            output_dir: Directory to write output to

        Returns:
            DocumentMetadata if successful, None if skipped
        """
        # Convert to Path objects and resolve
        file_path = Path(file_path).resolve()
        output_dir = Path(output_dir).resolve()

        # Skip files that are referenced in markdown files
        parent_dir = file_path.parent
        if parent_dir.name.startswith("20") and len(parent_dir.name) >= 8:
            # This is a dated directory, check if this file is referenced in the parent markdown file
            parent_md = parent_dir.parent / f"{parent_dir.name}.md"
            if parent_md.exists():
                try:
                    with open(parent_md, "r", encoding="utf-8") as f:
                        content = f.read()
                        # Check if this file is referenced in the markdown
                        file_name = str(file_path.relative_to(parent_dir))
                        if file_name in content:
                            logger.debug(f"Found reference to {file_name} in {parent_md}")
                            # Create metadata for the referenced file
                            metadata = DocumentMetadata.from_file(
                                file_path=file_path,
                                handler_name="reference",
                                handler_version="0.1.0",
                            )
                            metadata.processed = True
                            metadata.metadata["referenced_in"] = str(parent_md)
                            metadata.metadata["reference_type"] = "attachment"
                            # Update successful files count
                            self.pipeline.state[self.name]["successful_files"].add(file_path)
                            return metadata
                except Exception as e:
                    logger.error(f"Error checking references in {parent_md}: {str(e)}")
                    return None

        # Get handler for file type
        handler = self._get_handler(file_path)
        if not handler:
            logger.warning(f"No handler found for {file_path}")
            self.pipeline.state[self.name]["skipped_files"].add(file_path)
            self._update_stats(file_path.suffix.lower(), "skipped", None)
            return None

        try:
            # Process file with handler
            metadata = DocumentMetadata.from_file(
                file_path=file_path,
                handler_name=handler.name,
                handler_version=handler.version,
            )

            # Get relative path from input directory
            input_dir = Path(self.config.input_dir).resolve()
            try:
                rel_path = file_path.relative_to(input_dir)
            except ValueError:
                # If file is not under input directory, try to find a parent directory
                # that matches the input directory pattern
                for parent in file_path.parents:
                    if re.search(r"\d{8}", str(parent)):
                        # Use the path relative to this parent
                        remaining_path = file_path.relative_to(parent)
                        # Include the parent directory name in the relative path
                        rel_path = Path(parent.name) / remaining_path
                        break
                else:
                    # If no parent with date found, use just the filename
                    logger.warning(f"File {file_path} is not under input directory {input_dir}")
                    rel_path = Path(file_path.name)

            # Get output path preserving directory structure
            output_path = (
                self.pipeline.output_manager.get_phase_dir("parse")
                / rel_path.parent
                / f"{rel_path.stem}.parsed.md"
            )

            # Process file and update metadata
            result = await handler.process(file_path, metadata, output_path)
            if result.status == ProcessingStatus.COMPLETED:
                logger.info(f"Successfully processed {file_path}")
                self._update_stats(
                    file_path.suffix.lower(), "successful", handler.__class__.__name__
                )
                # Update successful files count
                self.pipeline.state[self.name]["successful_files"].add(file_path)
                return result.metadata
            else:
                logger.error(f"Failed to process {file_path}: {result.error}")
                self._update_stats(
                    file_path.suffix.lower(), "failed", handler.__class__.__name__
                )
                return None

        except Exception as e:
            logger.error(f"Failed to process {file_path}: {str(e)}")
            self._update_stats(
                file_path.suffix.lower(),
                "failed",
                handler.__class__.__name__ if handler else None,
            )
            return None

    def _update_stats(
        self, extension: str, status: str, handler: Optional[str]
    ) -> None:
        """Update statistics for file type.

        Args:
            extension: File extension
            status: Processing status (successful/failed/skipped)
            handler: Handler class name
        """
        if extension not in self.stats:
            self.stats[extension] = {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "skipped": 0,
                "unchanged": 0,
                "handlers": set(),
            }

        self.stats[extension]["total"] += 1
        self.stats[extension][status] += 1
        if handler:
            self.stats[extension]["handlers"].add(handler)

    def finalize(self) -> None:
        """Print phase summary and update pipeline stats."""
        logger.info("=== Parse Phase Summary ===")

        for extension, stats in self.stats.items():
            logger.info(f"\nFile type: {extension}")
            logger.info(f"Total files: {stats['total']}")
            logger.info(f"Successful: {stats['successful']}")
            logger.info(f"Failed: {stats['failed']}")
            logger.info(f"Skipped: {stats['skipped']}")
            logger.info(f"Unchanged: {stats['unchanged']}")
            logger.info(f"Handlers: {', '.join(stats['handlers'])}")

        # Log skipped files
        skipped_files = self.pipeline.state[self.name]["skipped_files"]
        if skipped_files:
            logger.warning(f"\nSkipped {len(skipped_files)} files:")
            for file in skipped_files:
                logger.warning(f"  - {file}")

        # Update pipeline state with stats
        if "stats" not in self.pipeline.state[self.name]:
            self.pipeline.state[self.name]["stats"] = {}
        self.pipeline.state[self.name]["stats"].update(self.stats)
