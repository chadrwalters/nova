"""Core Nova document processing system."""
import asyncio
import json
import logging
import os
import shutil
import tempfile
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from nova.config.manager import ConfigManager
from nova.core.logging import LoggingManager
from nova.core.metadata import FileMetadata
from nova.core.pipeline import NovaPipeline


class Nova:
    """Main Nova document processing system."""

    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        create_dirs: bool = True,
    ) -> None:
        """Initialize Nova system.

        Args:
            config_path: Path to configuration file. If not provided, will check
                environment variable NOVA_CONFIG_PATH, then fall back to default.
            create_dirs: Whether to create configured directories if they don't exist.
        """
        self.config = ConfigManager(config_path, create_dirs)

        # Initialize logging
        self.logging_manager = LoggingManager(self.config.config.logging)
        self.logger = self.logging_manager.get_logger("nova")

        # Initialize pipeline
        self.pipeline = NovaPipeline(config=self.config)
        self.output_manager = self.pipeline.output_manager

        self.logger.info(
            "Nova system initialized",
            extra={
                "context": {
                    "config_path": str(config_path) if config_path else "default",
                    "input_dir": str(self.config.input_dir),
                    "output_dir": str(self.config.output_dir),
                }
            },
        )

    def _save_metadata(self, metadata: Dict, output_dir: Path) -> None:
        """Save metadata to file.

        Args:
            metadata: Metadata to save.
            output_dir: Output directory.
        """
        try:
            # Get metadata file path using OutputManager
            file_path = Path(metadata["file_path"])
            metadata_file = self.output_manager.get_output_path_for_phase(
                file_path, "parse", ".metadata.json"
            )

            # Save metadata
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, default=str)

        except Exception as e:
            self.logger.error(f"Failed to save metadata: {str(e)}")

    def _safe_path(self, path: Union[str, Path]) -> Path:
        """Convert path to Path object safely.

        Args:
            path: Path to convert.

        Returns:
            Path object.
        """
        if path is None:
            return None

        try:
            # If already a Path, convert to string first
            path_str = str(path)

            # Handle Windows encoding
            safe_str = path_str.encode("cp1252", errors="replace").decode("cp1252")

            # Convert back to Path
            return Path(safe_str)
        except Exception:
            # If all else fails, use the path as is
            return Path(path)

    async def process_file(
        self, file_path: Path, output_dir: Path
    ) -> Optional[FileMetadata]:
        """Process a single file through the pipeline."""
        try:
            # Create a temporary directory for this file
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)

                # Create input directory and copy file
                input_dir = temp_dir_path / "input"
                input_dir.mkdir(parents=True)
                shutil.copy2(file_path, input_dir / file_path.name)

                # Process the directory
                await self.pipeline.process_directory(input_dir)

                # Copy the output files to the output directory
                output_dir.mkdir(parents=True, exist_ok=True)
                for phase_dir in (temp_dir_path / "processing" / "phases").glob("*"):
                    phase_output_dir = output_dir / phase_dir.name
                    phase_output_dir.mkdir(parents=True, exist_ok=True)
                    for output_file in phase_dir.rglob("*"):
                        if output_file.is_file():
                            relative_path = output_file.relative_to(phase_dir)
                            dest_path = phase_output_dir / relative_path
                            dest_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(output_file, dest_path)

                # Return metadata from the last processed file
                metadata_file = (
                    list(temp_dir_path.rglob("*.metadata.json"))[-1]
                    if list(temp_dir_path.rglob("*.metadata.json"))
                    else None
                )
                if metadata_file:
                    with open(metadata_file, "r") as f:
                        return FileMetadata.parse_raw(f.read())

                return None
        except Exception as e:
            self.logger.error(f"Failed to process file: {file_path}")
            self.logger.error(traceback.format_exc())
            return None

    async def process_directory(
        self,
        input_dir: Optional[Union[str, Path]] = None,
        output_dir: Optional[Union[str, Path]] = None,
        recursive: bool = True,
    ) -> List[FileMetadata]:
        """Process all files in directory.

        Args:
            input_dir: Input directory. If not provided,
                will use configured input directory.
            output_dir: Output directory. If not provided,
                will use configured output directory.
            recursive: Whether to process subdirectories.

        Returns:
            List of metadata about processed documents.
        """
        # Start timing
        start_time = time.time()

        # Convert paths safely
        input_dir = self._safe_path(input_dir or self.config.input_dir)
        output_dir = self._safe_path(
            output_dir or self.config.processing_dir / "phases" / "parse"
        )

        self.logger.info(f"Processing directory: {input_dir}")

        results = []
        errors = []
        pattern = "**/*" if recursive else "*"

        try:
            for file_path in input_dir.glob(pattern):
                if file_path.is_file():
                    try:
                        # Get relative path from input dir to maintain directory structure
                        # but skip the _NovaInput part if it exists
                        try:
                            rel_path = file_path.relative_to(input_dir)
                            # Always skip _NovaInput from the path parts
                            rel_path = Path(
                                *[p for p in rel_path.parts if p != "_NovaInput"]
                            )
                        except ValueError:
                            # If not under input_dir, just use the filename
                            rel_path = Path(file_path.name)

                        # If the input directory is named "test_files", preserve its structure
                        if input_dir.name == "test_files":
                            file_output_dir = output_dir / rel_path.parent
                        else:
                            # Otherwise, organize by file type and preserve subdirectories
                            ext = file_path.suffix.lower()
                            if ext in [".pdf", ".docx", ".doc", ".rtf", ".odt", ".txt"]:
                                category = "Documents"
                            elif ext in [".jpg", ".jpeg", ".png", ".gif", ".heic"]:
                                category = "Images"
                            elif ext in [".md"]:
                                category = "Notes"
                            else:
                                category = "Other"

                            # Create output directory preserving subdirectories but skip _NovaInput
                            if len(rel_path.parts) > 1:
                                file_output_dir = (
                                    output_dir / category / rel_path.parent
                                )
                            else:
                                file_output_dir = output_dir / category

                        metadata = await self.process_file(file_path, file_output_dir)
                        if metadata is not None:
                            results.append(metadata)
                    except Exception as e:
                        self.logger.error(f"Error processing {file_path}: {str(e)}")
                        errors.append(str(file_path))
                        continue

            self.logger.info(f"Processed {len(results)} files")

            if errors:
                self.logger.warning(f"Failed to process {len(errors)} files:")
                for error in errors:
                    self.logger.warning(f"  - {error}")

            return results

        except Exception as e:
            self.logger.error(f"Failed to process directory: {str(e)}")
            return []

    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats.

        Returns:
            List of supported file extensions.
        """
        return self.pipeline.get_supported_formats()
