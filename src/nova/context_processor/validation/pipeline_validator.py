"""Pipeline validator implementation."""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

from ..config.manager import ConfigManager
from ..core.reference_manager import ReferenceManager

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
        self.reference_manager = ReferenceManager()

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

            # Extract and validate references from all parsed files
            for parsed_file in parsed_files:
                try:
                    content = parsed_file.read_text(encoding="utf-8")
                    references = self.reference_manager.extract_references(content, parsed_file)
                    
                    # Validate references
                    validation_errors = self.reference_manager.validate_references(self.processing_dir)
                    if validation_errors:
                        self.errors.extend(validation_errors)
                        all_valid = False
                        files_with_errors += 1
                except Exception as e:
                    self.errors.append(f"Error processing references in {parsed_file}: {str(e)}")
                    all_valid = False
                    files_with_errors += 1

            # Check for invalid references
            invalid_refs = self.reference_manager.get_invalid_references()
            if invalid_refs:
                for ref in invalid_refs:
                    if ref.offset == 0:
                        self.errors.append(
                            f"Invalid reference at offset 0 in {ref.source_file}: "
                            f"[{ref.ref_type}:{ref.ref_id}]"
                        )
                all_valid = False

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
        logger.info(f"Files with errors: {files_with_errors}")
        logger.info(f"Invalid references: {len(self.reference_manager.get_invalid_references())}")

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
            # Only include .md files that are not in dated directories
            if f.is_file() and f.suffix.lower() == ".md":
                # Check if file is in a dated directory
                parent_dir = f.parent
                if not (parent_dir.name.startswith("20") and len(parent_dir.name) >= 8):
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

        # Track attachments for later validation
        self.attachments = {}

        # Validate each parsed file
        valid_files = set()
        for parsed_file in parsed_files:
            try:
                # Check if metadata exists in any of the expected locations
                metadata_found = False
                metadata = None
                
                # 1. Check in parse directory with full path structure
                try:
                    input_file = Path(parsed_file.stem.replace(".parsed", ""))
                    relative_path = input_file.relative_to(input_dir) if input_dir in input_file.parents else input_file
                    parse_metadata_path = self.parse_dir / relative_path.parent / f"{parsed_file.stem.replace('.parsed', '')}.metadata.json"
                    if parse_metadata_path.exists():
                        with open(parse_metadata_path, "r", encoding="utf-8") as f:
                            metadata = json.load(f)
                            metadata_found = True
                except Exception:
                    pass

                # 2. Check in original location
                if not metadata_found:
                    original_metadata_path = parsed_file.parent / f"{parsed_file.stem.replace('.parsed', '')}.metadata.json"
                    if original_metadata_path.exists():
                        try:
                            with open(original_metadata_path, "r", encoding="utf-8") as f:
                                metadata = json.load(f)
                                metadata_found = True
                        except Exception as e:
                            self.errors.append(
                                f"Error reading metadata file {original_metadata_path}: {str(e)}"
                            )

                # 3. Check in phase metadata directory
                if not metadata_found:
                    phase_metadata_path = self.parse_dir / "metadata" / f"{parsed_file.stem.replace('.parsed', '')}.metadata.json"
                    if phase_metadata_path.exists():
                        try:
                            with open(phase_metadata_path, "r", encoding="utf-8") as f:
                                metadata = json.load(f)
                                metadata_found = True
                        except Exception as e:
                            self.errors.append(
                                f"Error reading metadata file {phase_metadata_path}: {str(e)}"
                            )

                # Report missing metadata
                if not metadata_found:
                    self.errors.append(f"Missing metadata file: {parse_metadata_path}")
                    continue

                # Check if the file is in the correct directory structure
                try:
                    input_file = Path(metadata["original_path"])
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

                    # Add to attachments list
                    self.attachments[parent_dir].append({
                        "path": str(parsed_file),
                        "type": file_type,
                        "metadata": metadata
                    })

                valid_files.add(parsed_file)

            except Exception as e:
                self.errors.append(f"Error validating {parsed_file}: {str(e)}")

        return valid_files if valid_files else None

    def _validate_disassemble_phase(
        self, parsed_files: Set[Path]
    ) -> Optional[Dict[str, Dict[str, Path]]]:
        """Validate disassemble phase output.

        Args:
            parsed_files: Set of parsed files to validate

        Returns:
            Dict mapping base names to file paths if valid, None if invalid
        """
        if not self.disassemble_dir.exists():
            self.errors.append(
                f"Disassemble directory does not exist: {self.disassemble_dir}"
            )
            return None

        # Track disassembled files
        disassembled_files: Dict[str, Dict[str, Path]] = {}

        # Validate each parsed file
        for parsed_file in parsed_files:
            try:
                # Get base name without .parsed.md extension
                base_name = parsed_file.stem.replace(".parsed", "")

                # Get expected output files
                summary_file = self.disassemble_dir / f"{base_name}.summary.md"
                raw_notes_file = self.disassemble_dir / f"{base_name}.rawnotes.md"

                # Check if this is a main document or an attachment
                is_main_document = len(parsed_file.relative_to(self.parse_dir).parts) == 1

                # Read parsed content
                parsed_content = parsed_file.read_text(encoding="utf-8")

                # Split content into summary and raw notes
                parts = parsed_content.split(self.SPLIT_MARKER)
                parsed_summary = parts[0].strip() if parts else None
                parsed_raw_notes = parts[1].strip() if len(parts) > 1 else None

                # Validate summary file if it exists in the parsed content
                if parsed_summary is not None and parsed_summary.strip():
                    # Only check for summary files for files that have summary content
                    # and are not in a subdirectory (attachments)
                    if is_main_document:
                        if not summary_file.exists():
                            self.errors.append(
                                f"Missing summary file: {summary_file}"
                            )
                            continue
                        else:
                            summary_content = summary_file.read_text(
                                encoding="utf-8"
                            ).strip()
                            
                            # Normalize both contents for comparison
                            normalized_parsed = self._normalize_content(parsed_summary)
                            normalized_content = self._normalize_content(summary_content)
                            
                            if normalized_content != normalized_parsed:
                                # Check for error cases
                                if (
                                    "Error processing" not in parsed_content
                                    and "Warning: Encoding Issue" not in parsed_content
                                    and "<html" not in parsed_content
                                ):
                                    self.errors.append(
                                        f"Summary content mismatch in {summary_file}"
                                    )
                                    # Don't print the full content
                                    self.errors.append("Content mismatch detected. Run with --verbose for details.")
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
                            
                            # Normalize both contents for comparison
                            normalized_parsed = self._normalize_content(parsed_raw_notes)
                            normalized_content = self._normalize_content(raw_notes_content)
                            
                            if normalized_content != normalized_parsed:
                                # Check for error cases
                                if (
                                    "Error processing" not in parsed_content
                                    and "Warning: Encoding Issue" not in parsed_content
                                    and "<html" not in parsed_content
                                ):
                                    # Only show first 50 chars of each in error message
                                    self.errors.append(
                                        f"Raw notes content mismatch in {raw_notes_file}"
                                    )
                                    # Don't print the full content
                                    self.errors.append("Content mismatch detected. Run with --verbose for details.")
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
            # Get attachments file
            attachments_file = self.processing_dir / "Attachments.md"
            if not attachments_file.exists():
                self.errors.append("Attachments.md file not found")
                return False

            # Read attachments file content
            attachments_content = attachments_file.read_text(encoding="utf-8")

            # Extract and validate references in attachments file
            references = self.reference_manager.extract_references(attachments_content, attachments_file)
            validation_errors = self.reference_manager.validate_references(self.processing_dir)
            if validation_errors:
                # Truncate long error messages
                truncated_errors = [
                    self._truncate_content(error) for error in validation_errors
                ]
                self.errors.extend(truncated_errors)
                return False

            # Verify all attachments from parse phase are in the attachments file
            for parent_dir, attachments in self.attachments.items():
                for attachment in attachments:
                    error = self._validate_attachment_reference(attachment, attachments_content)
                    if error:
                        self.errors.append(error)
                        return False

            return True

        except Exception as e:
            self.errors.append(f"Error validating split phase: {str(e)}")
            return False

    def _truncate_content(self, content: str, max_length: int = 50) -> str:
        """Truncate content for error messages.
        
        Args:
            content: Content to truncate
            max_length: Maximum length before truncation
            
        Returns:
            Truncated content with ellipsis if needed
        """
        if not content:
            return ""
        # Remove newlines and extra whitespace
        content = " ".join(content.split())
        if len(content) <= max_length:
            return content
        return content[:max_length] + "..."

    def _validate_content_match(self, expected: str, actual: str, file_path: str) -> bool:
        """Validate that content matches expected value.
        
        Args:
            expected: Expected content
            actual: Actual content
            file_path: Path to file being validated
            
        Returns:
            True if content matches, False otherwise
        """
        if expected != actual:
            # Truncate content in error message
            truncated_expected = self._truncate_content(expected)
            truncated_actual = self._truncate_content(actual)
            
            self.errors.append(
                f"Content mismatch in {file_path}:\n"
                f"  Expected (truncated): {truncated_expected}\n"
                f"  Actual (truncated): {truncated_actual}"
            )
            return False
        return True

    def _validate_raw_notes(self, raw_notes_file: Path) -> bool:
        """Validate raw notes content.
        
        Args:
            raw_notes_file: Path to raw notes file
            
        Returns:
            True if validation passed, False otherwise
        """
        try:
            content = raw_notes_file.read_text(encoding="utf-8")
            
            # Basic content validation
            if not content.strip():
                self.errors.append(f"Empty raw notes file: {raw_notes_file}")
                return False
                
            # Size validation - increased to 10MB
            if len(content) > 10_000_000:  # 10MB limit
                # Split into chunks if over limit
                chunks = []
                current_size = 0
                current_chunk = []
                
                for line in content.split('\n'):
                    line_size = len(line.encode('utf-8'))
                    if current_size + line_size > 10_000_000:
                        # Save current chunk
                        chunk_content = '\n'.join(current_chunk)
                        chunks.append(chunk_content)
                        # Start new chunk
                        current_chunk = [line]
                        current_size = line_size
                    else:
                        current_chunk.append(line)
                        current_size += line_size
                
                # Add final chunk
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                
                # Write chunks to separate files
                for i, chunk in enumerate(chunks, 1):
                    chunk_file = raw_notes_file.parent / f"{raw_notes_file.stem}.part{i}.md"
                    chunk_file.write_text(chunk, encoding="utf-8")
                
                self.errors.append(
                    f"Raw notes content split into {len(chunks)} parts due to size limit: {raw_notes_file}"
                )
                return False
                
            return True
            
        except Exception as e:
            self.errors.append(f"Error reading raw notes file {raw_notes_file}: {str(e)}")
            return False

    def _normalize_content(self, content: str) -> str:
        """Normalize content for comparison by standardizing whitespace and line endings.
        
        Args:
            content: Content to normalize
            
        Returns:
            Normalized content string
        """
        if not content:
            return ""
            
        # Convert all line endings to \n and strip whitespace
        normalized = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Split into lines and normalize each line
        lines = []
        in_code_block = False
        code_block_indent = ""
        
        for line in normalized.split('\n'):
            # Handle code blocks
            if line.startswith('```'):
                in_code_block = not in_code_block
                if in_code_block:
                    code_block_indent = re.match(r'^(\s*)', line).group(1)
                lines.append(line.rstrip())
                continue
                
            # Preserve code block content exactly
            if in_code_block:
                # Remove only the code block indentation
                if line.startswith(code_block_indent):
                    line = line[len(code_block_indent):]
                lines.append(line.rstrip())
                continue
                
            # Skip empty lines
            if not line.strip():
                continue
                
            # Remove trailing whitespace
            line = line.rstrip()
            
            # Preserve indented code blocks (4 spaces or tab)
            if line.startswith('    ') or line.startswith('\t'):
                lines.append(line)
                continue
                
            # Normalize multiple spaces to single space for non-code content
            line = ' '.join(line.split())
            
            # Preserve markdown headers and list markers
            if re.match(r'^#{1,6}\s', line) or re.match(r'^[-*+]\s', line) or re.match(r'^\d+\.\s', line):
                lines.append(line)
                continue
                
            # Preserve link and image references
            if re.match(r'^\[.*?\]:', line):
                lines.append(line)
                continue
                
            # Normalize inline formatting
            # - Keep bold/italic markers but normalize their spacing
            line = re.sub(r'\*\*\s*(\S.*?\S)\s*\*\*', r'**\1**', line)
            line = re.sub(r'__\s*(\S.*?\S)\s*__', r'__\1__', line)
            line = re.sub(r'\*\s*(\S.*?\S)\s*\*', r'*\1*', line)
            line = re.sub(r'_\s*(\S.*?\S)\s*_', r'_\1_', line)
            
            # Normalize inline code
            line = re.sub(r'`\s*(\S.*?\S)\s*`', r'`\1`', line)
            
            # Normalize links and images
            line = re.sub(r'\[\s*(\S.*?\S)\s*\]\(\s*(\S+)\s*\)', r'[\1](\2)', line)
            line = re.sub(r'!\[\s*(\S.*?\S)\s*\]\(\s*(\S+)\s*\)', r'![\1](\2)', line)
            
            # Normalize HTML comments
            line = re.sub(r'<!--\s*(.*?)\s*-->', r'<!-- \1 -->', line)
            
            # Add normalized line
            lines.append(line)
            
        # Join lines with single newline
        normalized = '\n'.join(lines)
        
        # Remove multiple consecutive blank lines
        normalized = re.sub(r'\n{3,}', '\n\n', normalized)
        
        return normalized.strip()

    def _validate_attachment_reference(self, attachment: Dict[str, str], attachments_content: str) -> Optional[str]:
        """Validate a single attachment reference.

        Args:
            attachment: Attachment metadata dictionary
            attachments_content: Content of the attachments file

        Returns:
            Error message if validation fails, None if successful
        """
        # Get file path and extract base name without .parsed extension
        file_path = Path(attachment["path"])
        base_name = file_path.stem
        if base_name.endswith(".parsed"):
            base_name = base_name[:-7]

        # Check if attachment reference exists in content
        ref_marker = f"[ATTACH:{attachment['type']}:{base_name}]"
        if ref_marker not in attachments_content:
            # Try case-insensitive search
            if ref_marker.lower() not in attachments_content.lower():
                # Try finding similar references
                pattern = re.compile(r'\[ATTACH:[^:]+:([^\]]+)\]')
                existing_refs = pattern.findall(attachments_content)
                similar_refs = [ref for ref in existing_refs if self._similar_names(base_name, ref)]
                
                if similar_refs:
                    return (
                        f"Missing attachment reference in Attachments.md: {ref_marker}\n"
                        f"Similar references found: {', '.join(similar_refs)}"
                    )
                else:
                    return (
                        f"Missing attachment reference in Attachments.md: {ref_marker}\n"
                        f"No similar references found. Please check the file name and type."
                    )
        return None

    def _similar_names(self, name1: str, name2: str) -> bool:
        """Check if two names are similar.

        Args:
            name1: First name to compare
            name2: Second name to compare

        Returns:
            True if names are similar, False otherwise
        """
        # Convert to lowercase for comparison
        name1 = name1.lower()
        name2 = name2.lower()
        
        # Remove common file extensions
        name1 = re.sub(r'\.(md|txt|pdf|doc|docx|jpg|jpeg|png)$', '', name1)
        name2 = re.sub(r'\.(md|txt|pdf|doc|docx|jpg|jpeg|png)$', '', name2)
        
        # If one is a substring of the other, they're similar
        if name1 in name2 or name2 in name1:
            return True
        
        # Calculate Levenshtein distance
        if len(name1) > len(name2):
            name1, name2 = name2, name1
        
        distances = range(len(name1) + 1)
        for i2, c2 in enumerate(name2):
            distances_ = [i2+1]
            for i1, c1 in enumerate(name1):
                if c1 == c2:
                    distances_.append(distances[i1])
                else:
                    distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
            distances = distances_
        
        # Names are similar if Levenshtein distance is less than 1/3 of the longer name
        max_distance = len(name2) // 3
        return distances[-1] <= max_distance


def main() -> None:
    """Run pipeline validation."""
    parser = argparse.ArgumentParser(description="Validate Nova pipeline state")
    parser.add_argument(
        "--config",
        type=str,
        default="config/nova.yaml",
        help="Path to Nova config file",
    )
    args = parser.parse_args()

    # Load config
    config = ConfigManager.from_yaml(args.config)

    # Import pipeline here to avoid circular imports
    from ..core.pipeline import NovaPipeline

    # Create pipeline
    pipeline = NovaPipeline(config)

    # Create and run validator
    validator = PipelineValidator(pipeline)
    if not validator.validate():
        sys.exit(1)


if __name__ == "__main__":
    main()
