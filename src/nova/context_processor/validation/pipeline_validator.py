"""Pipeline validator implementation."""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Set

from ..config.manager import ConfigManager

if TYPE_CHECKING:
    from ..core.pipeline import NovaPipeline

logger = logging.getLogger(__name__)


class PipelineValidator:
    """Validates pipeline state and outputs."""

    # Marker used to split sections in parsed files
    SPLIT_MARKER = "--==RAW NOTES==--"

    def __init__(self, pipeline: "NovaPipeline") -> None:
        """Initialize validator.

        Args:
            pipeline: Pipeline instance
        """
        self.pipeline = pipeline
        self.config = pipeline.config
        self.errors: List[str] = []
        self.attachments: Dict[str, List[Dict]] = {}

        # Get phase directories from pipeline config
        self.processing_dir = self.pipeline.config.processing_dir
        self.parse_dir = self.processing_dir / "phases" / "parse"
        self.disassemble_dir = self.processing_dir / "phases" / "disassemble"
        self.split_dir = self.processing_dir / "phases" / "split"
        self.finalize_dir = self.processing_dir / "phases" / "finalize"

        # Ensure all phase directories exist
        for phase_dir in [
            self.parse_dir,
            self.disassemble_dir,
            self.split_dir,
            self.finalize_dir,
        ]:
            phase_dir.mkdir(parents=True, exist_ok=True)

    def validate(self) -> bool:
        """Run validation checks for all phases.

        Returns:
            True if validation passes, False otherwise
        """
        if not self.processing_dir.exists():
            self.errors.append(
                f"Processing directory does not exist: {self.processing_dir}"
            )
            return False

        # Track validation results
        all_valid = True
        files_checked = 0
        files_with_errors = 0

        # Validate parse phase
        parsed_files = self._validate_parse_phase()
        if parsed_files is None:
            all_valid = False
        else:
            files_checked += len(parsed_files)

            # Validate disassemble phase
            disassembled_files = self._validate_disassemble_phase(parsed_files)
            if disassembled_files is None:
                all_valid = False
            else:
                # Validate split phase
                if not self._validate_split_phase(disassembled_files):
                    all_valid = False

        # Log summary
        logger.info(f"Validation complete:")
        logger.info(f"Files checked: {files_checked}")
        logger.info(f"Files with errors: {len(self.errors)}")

        if self.errors:
            logger.error("Validation errors:")
            for error in self.errors:
                logger.error(f"  - {error}")
            all_valid = False

        return all_valid

    def _validate_parse_phase(self) -> Optional[Set[Path]]:
        """Validate parse phase output.

        Returns:
            Set of parsed markdown files if valid, None if invalid
        """
        if not self.parse_dir.exists():
            self.errors.append(f"Parse directory does not exist: {self.parse_dir}")
            return None

        # Get all input files
        input_dir = Path(self.processing_dir).parent / "_NovaInput"
        if not input_dir.exists():
            self.errors.append(f"Input directory does not exist: {input_dir}")
            return None

        # Get all input markdown files (excluding hidden files and directories without .md files)
        input_files = set()
        for f in input_dir.rglob("*"):
            # Skip hidden files and directories
            if any(part.startswith(".") for part in f.parts):
                continue
            # Only include .md files
            if f.is_file() and f.suffix.lower() == ".md":
                input_files.add(f)

        # Get all parsed files
        parsed_files = set(f for f in self.parse_dir.rglob("*.parsed.md"))
        if not parsed_files:
            self.errors.append("No parsed files found")
            return None

        # Get primary content files (markdown files not in subdirectories)
        primary_content_files = {
            f for f in parsed_files if len(f.relative_to(self.parse_dir).parts) == 1
        }

        # Check if we have the right number of primary content files
        if len(primary_content_files) != len(input_files):
            self.errors.append(
                f"Number of parsed files ({len(primary_content_files)}) does not match number of input markdown files ({len(input_files)})"
            )

            # List missing files
            parsed_stems = {
                f.stem.replace(".parsed", "") for f in primary_content_files
            }
            input_stems = {f.stem for f in input_files}
            missing_files = input_stems - parsed_stems
            if missing_files:
                self.errors.append("Missing parsed files for:")
                for missing in missing_files:
                    self.errors.append(f"  - {missing}")

            extra_files = parsed_stems - input_stems
            if extra_files:
                self.errors.append("Extra parsed files found:")
                for extra in extra_files:
                    self.errors.append(f"  - {extra}")

        # Track attachments for later validation
        self.attachments = {}

        # Validate each parsed file
        valid_files = set()
        for parsed_file in parsed_files:
            try:
                # Check if metadata exists
                base_path = parsed_file.parent / parsed_file.stem.replace(".parsed", "")
                metadata_file = base_path.with_suffix(".metadata.json")
                if not metadata_file.exists():
                    # Try with just the base name
                    metadata_file = (
                        parsed_file.parent
                        / f"{parsed_file.stem.replace('.parsed', '')}.metadata.json"
                    )
                    if not metadata_file.exists():
                        self.errors.append(f"Missing metadata file: {metadata_file}")
                        continue

                # Validate metadata format
                try:
                    with open(metadata_file, "r") as file_handle:
                        metadata = json.load(file_handle)
                    if not isinstance(metadata, dict):
                        self.errors.append(
                            f"Invalid metadata format in {metadata_file}"
                        )
                        continue

                    # Check if the metadata has the required fields
                    required_fields = [
                        "file_path",
                        "handler_name",
                        "handler_version",
                        "processed",
                    ]
                    missing_fields = [f for f in required_fields if f not in metadata]
                    if missing_fields:
                        self.errors.append(
                            f"Missing required fields in {metadata_file}: {', '.join(missing_fields)}"
                        )
                        continue

                except json.JSONDecodeError:
                    self.errors.append(
                        f"Invalid JSON in metadata file: {metadata_file}"
                    )
                    continue

                # Check if the file is in the correct directory structure
                try:
                    input_file = Path(metadata["file_path"])
                    expected_rel_path = input_file.relative_to(input_dir)
                    actual_rel_path = parsed_file.relative_to(self.parse_dir)

                    # The paths should match except for the .parsed.md extension
                    expected_path = (
                        self.parse_dir
                        / expected_rel_path.parent
                        / f"{expected_rel_path.stem}.parsed.md"
                    )
                    if parsed_file != expected_path:
                        self.errors.append(
                            f"File {parsed_file} is in the wrong location. Should be at {expected_path}"
                        )
                        continue
                except ValueError:
                    self.errors.append(
                        f"File {parsed_file} is not in the correct directory structure"
                    )
                    continue

                # Check if assets directory exists if referenced in metadata
                if metadata.get("has_assets", False):
                    assets_dir = parsed_file.parent / f"{parsed_file.stem}.assets"
                    if not assets_dir.exists():
                        self.errors.append(f"Missing assets directory: {assets_dir}")
                        continue

                # Track attachments if this is a subdirectory file
                if len(parsed_file.relative_to(self.parse_dir).parts) > 1:
                    # Get the parent document name from the directory name
                    parent_dir = parsed_file.parent.name
                    if parent_dir not in self.attachments:
                        self.attachments[parent_dir] = []

                    # Get file type from extension
                    file_ext = parsed_file.suffix.lower()
                    file_type = {
                        ".pdf": "PDF",
                        ".doc": "DOC",
                        ".docx": "DOC",
                        ".xls": "EXCEL",
                        ".xlsx": "EXCEL",
                        ".csv": "EXCEL",
                        ".txt": "TXT",
                        ".json": "JSON",
                        ".png": "IMAGE",
                        ".jpg": "IMAGE",
                        ".jpeg": "IMAGE",
                        ".heic": "IMAGE",
                        ".svg": "IMAGE",
                        ".gif": "IMAGE",
                    }.get(file_ext, "OTHER")

                    # Only read content for text files
                    content = (
                        parsed_file.read_text(encoding="utf-8").strip()
                        if file_type not in ["IMAGE", "PDF", "EXCEL", "DOC", "OTHER"]
                        and not parsed_file.name.startswith(
                            "."
                        )  # Skip hidden files like .DS_Store
                        else f"Binary file: {parsed_file.name}"
                    )

                    self.attachments[parent_dir].append(
                        {
                            "path": parsed_file,
                            "content": content,
                        }
                    )

                valid_files.add(parsed_file)

            except Exception as e:
                self.errors.append(f"Error validating {parsed_file}: {str(e)}")

        return valid_files if valid_files else None

    def _validate_disassemble_phase(
        self, parsed_files: Set[Path]
    ) -> Optional[Dict[str, Dict[str, Path]]]:
        """Validate disassemble phase output.

        Args:
            parsed_files: Set of valid parsed markdown files

        Returns:
            Dict mapping base names to disassembled files if valid, None if invalid
        """
        if not self.disassemble_dir.exists():
            self.errors.append(
                f"Disassemble directory does not exist: {self.disassemble_dir}"
            )
            return None

        # Track disassembled files
        disassembled_files = {}

        # Check each parsed file has corresponding disassembled files
        for parsed_file in parsed_files:
            base_name = parsed_file.stem.replace(".parsed", "")

            # Get expected disassembled files
            summary_file = self.disassemble_dir / f"{base_name}.summary.md"
            raw_notes_file = self.disassemble_dir / f"{base_name}.rawnotes.md"

            try:
                # Read parsed content
                parsed_content = parsed_file.read_text(encoding="utf-8")

                # Check if this is a main document (not in a subdirectory)
                is_main_document = (
                    len(parsed_file.relative_to(self.parse_dir).parts) == 1
                )

                # Split content
                if self.SPLIT_MARKER in parsed_content:
                    parsed_summary, parsed_raw_notes = parsed_content.split(
                        self.SPLIT_MARKER, maxsplit=1
                    )
                    parsed_summary = parsed_summary.strip()
                    parsed_raw_notes = parsed_raw_notes.strip()
                else:
                    parsed_summary = parsed_content.strip()
                    parsed_raw_notes = None

                # Validate summary file
                if not summary_file.exists():
                    # Only check for summary files for main documents
                    if parsed_summary and is_main_document:
                        self.errors.append(f"Missing summary file: {summary_file}")
                        continue
                elif is_main_document:
                    summary_content = summary_file.read_text(encoding="utf-8").strip()
                    if summary_content != parsed_summary:
                        # Check for error cases
                        if (
                            "Error processing" not in parsed_content
                            and "Warning: Encoding Issue" not in parsed_content
                            and "<html" not in parsed_content
                        ):
                            self.errors.append(
                                f"Summary content mismatch in {summary_file}"
                            )
                            self.errors.append(f"Expected: {parsed_summary}")
                            self.errors.append(f"Got: {summary_content}")
                        continue

                # Validate raw notes file if it exists in the parsed content
                if parsed_raw_notes is not None and parsed_raw_notes.strip():
                    # Only check for raw notes files for files that have raw notes content
                    # and are not in a subdirectory (attachments)
                    if is_main_document:
                        if not raw_notes_file.exists():
                            self.errors.append(
                                f"Missing raw notes file: {raw_notes_file}"
                            )
                            continue
                        else:
                            raw_notes_content = raw_notes_file.read_text(
                                encoding="utf-8"
                            ).strip()
                            if raw_notes_content != parsed_raw_notes:
                                # Check for error cases
                                if (
                                    "Error processing" not in parsed_content
                                    and "Warning: Encoding Issue" not in parsed_content
                                    and "<html" not in parsed_content
                                ):
                                    self.errors.append(
                                        f"Raw notes content mismatch in {raw_notes_file}"
                                    )
                                    self.errors.append(f"Expected: {parsed_raw_notes}")
                                    self.errors.append(f"Got: {raw_notes_content}")
                                continue

                # Track valid files
                disassembled_files[base_name] = {
                    "summary": summary_file if is_main_document else None,
                    "raw_notes": raw_notes_file
                    if is_main_document and raw_notes_file.exists()
                    else None,
                }

            except Exception as e:
                self.errors.append(
                    f"Error validating disassembly of {parsed_file}: {str(e)}"
                )

        return disassembled_files if disassembled_files else None

    def _validate_split_phase(
        self, disassembled_files: Dict[str, Dict[str, Path]]
    ) -> bool:
        """Validate the split phase output.

        Args:
            disassembled_files: Dict mapping section types to file paths

        Returns:
            True if validation passed, False otherwise
        """
        try:
            # Get split phase output directory
            split_dir = self.pipeline.config.processing_dir / "phases" / "split"
            if not split_dir.exists():
                self.errors.append("Split phase output directory not found")
                return False

            # Check for consolidated files
            summary_file = split_dir / "Summary.md"
            raw_notes_file = split_dir / "Raw Notes.md"
            attachments_file = split_dir / "Attachments.md"

            # Verify files exist
            if not summary_file.exists():
                self.errors.append("Summary.md file not found")
                return False
            if not raw_notes_file.exists():
                self.errors.append("Raw Notes.md file not found")
                return False
            if not attachments_file.exists():
                self.errors.append("Attachments.md file not found")
                return False

            # Read attachments file content
            attachments_content = attachments_file.read_text(encoding="utf-8")

            # Verify all attachments from parse phase are in the attachments file
            for parent_dir, attachments in self.attachments.items():
                for attachment in attachments:
                    # Get file path and extract base name without .parsed extension
                    file_path = Path(attachment["path"])
                    base_name = file_path.stem
                    if base_name.endswith(".parsed"):
                        base_name = base_name[:-7]

                    # Get file extension from original path
                    file_ext = file_path.suffix.lower()

                    # Map file extensions to attachment types
                    ext_to_type = {
                        ".pdf": "PDF",
                        ".doc": "DOC",
                        ".docx": "DOC",
                        ".xls": "EXCEL",
                        ".xlsx": "EXCEL",
                        ".csv": "EXCEL",
                        ".txt": "TXT",
                        ".json": "JSON",
                        ".png": "IMAGE",
                        ".jpg": "IMAGE",
                        ".jpeg": "IMAGE",
                        ".heic": "IMAGE",
                        ".svg": "IMAGE",
                        ".gif": "IMAGE",
                    }
                    attachment_type = ext_to_type.get(file_ext, "OTHER")

                    # Get base name without extension
                    base_stem = Path(base_name).stem
                    # Create variations of the base name
                    ref_variations = [
                        base_stem,  # Original with spaces
                        base_stem.replace(" ", "_"),  # With underscores
                        base_stem.replace(" ", "-"),  # With hyphens
                        base_stem.replace(" ", ""),  # No spaces
                    ]

                    # Flag to track if we found a reference
                    found_ref = False

                    # Try each variation
                    for ref_base in ref_variations:
                        # Try different attachment type variations
                        type_variations = [
                            attachment_type,  # Original type
                            attachment_type.lower(),  # Lowercase type
                            attachment_type.upper(),  # Uppercase type
                            attachment_type.capitalize(),  # Capitalized type
                        ]

                        # Also try other common types for the same file
                        if attachment_type == "DOC":
                            type_variations.extend(
                                ["PDF", "EXCEL", "TXT", "JSON", "IMAGE"]
                            )
                        elif attachment_type == "IMAGE":
                            type_variations.extend(["DOC", "PDF"])
                        elif attachment_type == "PDF":
                            type_variations.extend(["DOC", "IMAGE"])
                        elif attachment_type == "EXCEL":
                            type_variations.extend(["DOC", "CSV"])
                        elif attachment_type == "TXT":
                            type_variations.extend(["DOC", "JSON"])
                        elif attachment_type == "JSON":
                            type_variations.extend(["DOC", "TXT"])
                        elif attachment_type == "CSV":
                            type_variations.extend(["DOC", "EXCEL"])

                        # Try each type variation
                        for ref_type in type_variations:
                            # Create reference pattern
                            ref_pattern = f"[ATTACH:{ref_type}:{ref_base}]"

                            # Check for exact match
                            if ref_pattern in attachments_content:
                                found_ref = True
                                break

                            # Try with file extension
                            if "." in ref_base:
                                # Try without extension
                                base_without_ext = Path(ref_base).stem
                                ref_pattern_no_ext = (
                                    f"[ATTACH:{ref_type}:{base_without_ext}]"
                                )
                                if ref_pattern_no_ext in attachments_content:
                                    found_ref = True
                                    break

                            # Try with file extension
                            ref_pattern_with_ext = (
                                f"[ATTACH:{ref_type}:{ref_base}.{file_ext[1:]}]"
                            )
                            if ref_pattern_with_ext in attachments_content:
                                found_ref = True
                                break

                        if found_ref:
                            break

                    if not found_ref:
                        # Get the original file name without any extensions
                        original_name = Path(base_name).stem
                        if original_name.endswith(".parsed"):
                            original_name = original_name[:-7]
                        
                        # Try to find any reference that contains this name
                        ref_found = False
                        for line in attachments_content.split("\n"):
                            # Look for reference markers
                            if "Reference: [ATTACH:" in line:
                                # Extract the reference
                                ref_start = line.find("[ATTACH:")
                                ref_end = line.find("]", ref_start)
                                if ref_start >= 0 and ref_end > ref_start:
                                    ref = line[ref_start:ref_end + 1]
                                    # Split into parts
                                    parts = ref[1:-1].split(":")  # Remove [] and split
                                    if len(parts) == 3:
                                        # Compare the name part
                                        ref_name = parts[2]
                                        # Check if either name contains the other
                                        if original_name in ref_name or ref_name in original_name:
                                            ref_found = True
                                            break
                        
                        if not ref_found:
                            self.errors.append(
                                f"No attachment reference found for {original_name} in consolidated Attachments.md"
                            )

            return True

        except Exception as e:
            self.errors.append(f"Error validating split phase: {str(e)}")
            return False


def main() -> None:
    """Run pipeline validation."""
    parser = argparse.ArgumentParser(description="Validate pipeline output")
    parser.add_argument("--config", help="Path to config file")
    args = parser.parse_args()

    # Initialize pipeline
    from ..core.pipeline import NovaPipeline

    pipeline = NovaPipeline(args.config)

    # Run validation
    validator = PipelineValidator(pipeline)
    success = validator.validate()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
