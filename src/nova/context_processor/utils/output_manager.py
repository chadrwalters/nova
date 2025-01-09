"""Centralized output file management for Nova."""

# Standard library
import logging
from pathlib import Path
from typing import Optional, Union
import re

# Internal imports
from ..config.manager import ConfigManager

logger = logging.getLogger(__name__)


class OutputManager:
    """Manages output file paths and organization."""

    def __init__(self, config: ConfigManager) -> None:
        """Initialize output manager.

        Args:
            config: Nova configuration manager
        """
        self.config = config

    def get_phase_dir(self, phase: str) -> Path:
        """Get directory for a phase.

        Args:
            phase: Phase to get directory for

        Returns:
            Directory for phase
        """
        # Build phase directory path
        phase_dir = Path(self.config.processing_dir) / "phases" / phase

        # Ensure directory exists
        phase_dir.mkdir(parents=True, exist_ok=True)

        return phase_dir

    def get_relative_path(self, file_path: Union[str, Path]) -> Path:
        """Get relative path from input directory.

        Args:
            file_path: Path to get relative path for

        Returns:
            Relative path from input directory
        """
        # Convert to Path object and resolve
        file_path = Path(file_path).resolve()
        input_dir = Path(self.config.input_dir).resolve()

        try:
            # Try to get relative path from input directory
            rel_path = file_path.relative_to(input_dir)
            return rel_path
        except ValueError:
            # If file is not under input directory, try to find a parent directory
            # that matches the input directory pattern
            for parent in file_path.parents:
                try:
                    # Check if this parent directory contains a date pattern
                    if re.search(r"\d{8}", str(parent)):
                        # Use the path relative to this parent
                        rel_path = file_path.relative_to(parent)
                        # Include the parent directory name in the relative path
                        return Path(parent.name) / rel_path
                except ValueError:
                    continue

            # If no suitable parent found, use filename only
            logger.warning(f"File {file_path} is not under input directory {input_dir}")
            return Path(file_path.name)

    def get_output_path_for_phase(
        self, rel_path: Union[str, Path], phase: str, suffix: str = ""
    ) -> Path:
        """Get output path for a file in a phase.

        Args:
            rel_path: Relative path from input directory
            phase: Phase to get output path for
            suffix: Optional suffix to add to filename

        Returns:
            Output path for file
        """
        # Convert to Path object
        rel_path = Path(rel_path)

        # Get phase directory
        phase_dir = self.get_phase_dir(phase)

        # Create output directory preserving structure
        output_path = phase_dir / rel_path.parent

        # Get the stem without any existing extensions
        stem = rel_path.stem
        while "." in stem:
            stem = stem.rsplit(".", 1)[0]

        # Clean up the stem
        stem = re.sub(r'[<>:"/\\|?*!@#$%^&(){}\[\]]', "_", stem)
        stem = re.sub(r"[\s_]+", "_", stem)
        stem = stem.strip(". _")

        # Add filename with suffix and .md extension
        if suffix and not suffix.startswith("."):
            suffix = "." + suffix

        # Create a sanitized output path
        output_path = output_path / f"{stem}{suffix}.md"

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        return output_path

    def get_directory_for_phase(
        self, input_file: Union[str, Path], phase_name: str, create: bool = True
    ) -> Path:
        """Get output directory for a file in a specific phase.

        Args:
            input_file: Input file path
            phase_name: Name of the phase
            create: Whether to create the directory

        Returns:
            Path to output directory
        """
        input_file = Path(input_file)

        # Build base directory path
        output_base = self.config.processing_dir / "phases" / phase_name

        # Always try to get path relative to input directory first
        try:
            relative_path = input_file.relative_to(self.config.input_dir)
        except ValueError:
            # If not under input_dir, try to find a parent directory that contains a date
            for parent in input_file.parents:
                if re.search(r"\d{8}", str(parent)):
                    # Use the path relative to this parent
                    remaining_path = input_file.relative_to(parent)
                    # Include the parent directory name in the relative path
                    relative_path = Path(parent.name) / remaining_path
                    break
            else:
                # If no parent with date found, check if it's in a subdirectory of an input file
                for parent in input_file.parents:
                    try:
                        # Try to find a parent that's relative to input_dir
                        parent_rel = parent.relative_to(self.config.input_dir)
                        # If found, use the remaining path from there
                        remaining_path = input_file.relative_to(parent)
                        relative_path = parent_rel / remaining_path
                        break
                    except ValueError:
                        continue
                else:
                    # If no parent is under input_dir, use just the filename
                    relative_path = Path(input_file.name)

        # Get the base name without any extensions
        stem = relative_path.stem
        while "." in stem:
            stem = stem.rsplit(".", 1)[0]

        # Remove any existing .parsed or .metadata suffix from the stem
        while True:
            if stem.endswith(".parsed"):
                stem = stem[:-7]  # Remove '.parsed' suffix
            elif stem.endswith(".metadata"):
                stem = stem[:-9]  # Remove '.metadata' suffix
            else:
                break

        # Clean up the stem
        stem = re.sub(r'[<>:"/\\|?*!@#$%^&(){}\[\]]', "_", stem)
        stem = re.sub(r"[\s_]+", "_", stem)
        stem = stem.strip(". _")

        # Construct the output directory path preserving directory structure
        # If the file is in a subdirectory, use that structure
        if relative_path.parent != Path("."):
            # Clean up parent directory names
            clean_parent = str(relative_path.parent)
            clean_parent = re.sub(r'[<>:"/\\|?*!@#$%^&(){}\[\]]', "_", clean_parent)
            clean_parent = re.sub(r"[\s_]+", "_", clean_parent)
            clean_parent = clean_parent.strip(". _")
            output_dir = output_base / clean_parent / stem
        else:
            output_dir = output_base / stem

        # Check for existing directories with the same base name
        if create:
            # Look for existing directories with the same base name
            existing_dirs = []
            for item in output_base.glob(f"**/{stem}*"):
                if item.is_dir():
                    # Check if this is a variant directory
                    item_stem = item.name
                    while "." in item_stem:
                        item_stem = item_stem.rsplit(".", 1)[0]
                    if item_stem == stem:
                        existing_dirs.append(item)

            if existing_dirs:
                # If there are existing directories, merge them into one
                target_dir = output_dir
                target_dir.mkdir(parents=True, exist_ok=True)
                
                for existing_dir in existing_dirs:
                    if existing_dir != target_dir:
                        try:
                            # Move all files from existing directory to target
                            for item in existing_dir.glob("**/*"):
                                if item.is_file():
                                    # Get relative path from existing directory
                                    rel_path = item.relative_to(existing_dir)
                                    # Create target path
                                    target_path = target_dir / rel_path
                                    # Ensure parent directory exists
                                    target_path.parent.mkdir(parents=True, exist_ok=True)
                                    # Move file if it doesn't exist or has different content
                                    if not target_path.exists():
                                        item.rename(target_path)
                                    else:
                                        # Compare file contents
                                        with open(item, 'rb') as src, open(target_path, 'rb') as dst:
                                            import hashlib
                                            src_hash = hashlib.md5(src.read()).hexdigest()
                                            dst_hash = hashlib.md5(dst.read()).hexdigest()
                                            if src_hash != dst_hash:
                                                # Files are different, keep both with unique names
                                                counter = 1
                                                while True:
                                                    new_path = target_path.parent / f"{target_path.stem}_{counter}{target_path.suffix}"
                                                    if not new_path.exists():
                                                        item.rename(new_path)
                                                        break
                                                    counter += 1
                            # Remove empty directory
                            import shutil
                            shutil.rmtree(existing_dir)
                        except Exception as e:
                            logger.warning(f"Failed to merge directory {existing_dir}: {e}")
            else:
                # Create new directory
                output_dir.mkdir(parents=True, exist_ok=True)

        return output_dir

    def copy_file(
        self, source: Path, destination: Path, overwrite: bool = True
    ) -> bool:
        """Copy a file, creating parent directories if needed.

        Args:
            source: Source file path
            destination: Destination file path
            overwrite: Whether to overwrite existing files

        Returns:
            True if file was copied, False if skipped
        """
        try:
            if not source.exists():
                self.logger.warning(f"Source file does not exist: {source}")
                return False

            if destination.exists() and not overwrite:
                self.logger.debug(f"Skipping existing file: {destination}")
                return False

            # Ensure parent directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            destination.write_bytes(source.read_bytes())
            return True

        except Exception as e:
            self.logger.error(f"Failed to copy {source} to {destination}: {str(e)}")
            return False
