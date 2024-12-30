"""Pipeline validation script."""

import argparse
from pathlib import Path
import logging
from typing import Dict, List, Set, Tuple, Optional
import sys
import json

logger = logging.getLogger(__name__)

class PipelineValidator:
    """Validator for Nova pipeline phases."""
    
    SPLIT_MARKER = "--==RAW NOTES==--"
    
    def __init__(self, processing_dir: Path):
        """Initialize validator.
        
        Args:
            processing_dir: Root directory containing all phase outputs
        """
        self.processing_dir = Path(processing_dir)
        self.parse_dir = self.processing_dir / "phases" / "parse"
        self.disassemble_dir = self.processing_dir / "phases" / "disassemble"
        self.split_dir = self.processing_dir / "phases" / "split"
        self.errors: List[str] = []
        
    def validate(self) -> bool:
        """Run validation checks for all phases.
        
        Returns:
            True if validation passes, False otherwise
        """
        if not self.processing_dir.exists():
            self.errors.append(f"Processing directory does not exist: {self.processing_dir}")
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
                
        return all_valid
        
    def _validate_parse_phase(self) -> Optional[Set[Path]]:
        """Validate parse phase output.
        
        Returns:
            Set of parsed markdown files if valid, None if invalid
        """
        if not self.parse_dir.exists():
            self.errors.append(f"Parse directory does not exist: {self.parse_dir}")
            return None
            
        # Get all parsed markdown files
        parsed_files = set(f for f in self.parse_dir.rglob("*.parsed.md"))
        if not parsed_files:
            self.errors.append("No parsed markdown files found")
            return None
            
        # Track attachments for later validation
        self.attachments = {}
            
        # Validate each parsed file
        valid_files = set()
        for parsed_file in parsed_files:
            try:
                # Check if metadata exists
                base_path = parsed_file.parent / parsed_file.stem.replace('.parsed', '')
                metadata_file = base_path.with_suffix('.metadata.json')
                if not metadata_file.exists():
                    self.errors.append(f"Missing metadata file: {metadata_file}")
                    continue
                    
                # Validate metadata format
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    if not isinstance(metadata, dict):
                        self.errors.append(f"Invalid metadata format in {metadata_file}")
                        continue
                except json.JSONDecodeError:
                    self.errors.append(f"Invalid JSON in metadata file: {metadata_file}")
                    continue
                    
                # Check if assets directory exists if referenced in metadata
                if metadata.get('has_assets', False):
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
                    self.attachments[parent_dir].append({
                        'path': parsed_file,
                        'content': parsed_file.read_text(encoding='utf-8').strip()
                    })
                        
                valid_files.add(parsed_file)
                
            except Exception as e:
                self.errors.append(f"Error validating {parsed_file}: {str(e)}")
                
        return valid_files if valid_files else None
        
    def _validate_disassemble_phase(self, parsed_files: Set[Path]) -> Optional[Dict[str, Dict[str, Path]]]:
        """Validate disassemble phase output.
        
        Args:
            parsed_files: Set of valid parsed markdown files
            
        Returns:
            Dict mapping base names to disassembled files if valid, None if invalid
        """
        if not self.disassemble_dir.exists():
            self.errors.append(f"Disassemble directory does not exist: {self.disassemble_dir}")
            return None
            
        # Track disassembled files
        disassembled_files = {}
        
        # Check each parsed file has corresponding disassembled files
        for parsed_file in parsed_files:
            base_name = parsed_file.stem.replace('.parsed', '')
            
            # Get expected disassembled files
            summary_file = self.disassemble_dir / f"{base_name}.summary.md"
            raw_notes_file = self.disassemble_dir / f"{base_name}.rawnotes.md"
            
            try:
                # Read parsed content
                parsed_content = parsed_file.read_text(encoding='utf-8')
                
                # Check if this is a main document (not in a subdirectory)
                is_main_document = len(parsed_file.relative_to(self.parse_dir).parts) == 1
                
                # Split content
                if self.SPLIT_MARKER in parsed_content:
                    parsed_summary, parsed_raw_notes = parsed_content.split(self.SPLIT_MARKER, maxsplit=1)
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
                    summary_content = summary_file.read_text(encoding='utf-8').strip()
                    if summary_content != parsed_summary:
                        # Check for error cases
                        if "Error processing" not in parsed_content and "Warning: Encoding Issue" not in parsed_content and "<html" not in parsed_content:
                            self.errors.append(f"Summary content mismatch in {summary_file}")
                            self.errors.append(f"Expected: {parsed_summary}")
                            self.errors.append(f"Got: {summary_content}")
                        continue
                        
                # Validate raw notes file if it exists in the parsed content
                if parsed_raw_notes is not None and parsed_raw_notes.strip():
                    # Only check for raw notes files for files that have raw notes content
                    # and are not in a subdirectory (attachments)
                    if is_main_document:
                        if not raw_notes_file.exists():
                            self.errors.append(f"Missing raw notes file: {raw_notes_file}")
                            continue
                        else:
                            raw_notes_content = raw_notes_file.read_text(encoding='utf-8').strip()
                            if raw_notes_content != parsed_raw_notes:
                                # Check for error cases
                                if "Error processing" not in parsed_content and "Warning: Encoding Issue" not in parsed_content and "<html" not in parsed_content:
                                    self.errors.append(f"Raw notes content mismatch in {raw_notes_file}")
                                    self.errors.append(f"Expected: {parsed_raw_notes}")
                                    self.errors.append(f"Got: {raw_notes_content}")
                                continue
                            
                # Track valid files
                disassembled_files[base_name] = {
                    'summary': summary_file if is_main_document else None,
                    'raw_notes': raw_notes_file if is_main_document and raw_notes_file.exists() else None
                }
                
            except Exception as e:
                self.errors.append(f"Error validating disassembly of {parsed_file}: {str(e)}")
                
        return disassembled_files if disassembled_files else None
        
    def _validate_split_phase(self, disassembled_files: Dict[str, Dict[str, Path]]) -> bool:
        """Validate split phase output.
        
        Args:
            disassembled_files: Dict mapping base names to disassembled files
            
        Returns:
            True if valid, False otherwise
        """
        if not self.split_dir.exists():
            self.errors.append(f"Split directory does not exist: {self.split_dir}")
            return False
            
        # Check consolidated files exist
        summary_file = self.split_dir / "Summary.md"
        raw_notes_file = self.split_dir / "Raw Notes.md"
        attachments_file = self.split_dir / "Attachments.md"
        
        if not summary_file.exists():
            self.errors.append(f"Missing consolidated summary file: {summary_file}")
            return False
            
        if not raw_notes_file.exists():
            self.errors.append(f"Missing consolidated raw notes file: {raw_notes_file}")
            return False
            
        if not attachments_file.exists():
            self.errors.append(f"Missing consolidated attachments file: {attachments_file}")
            return False
            
        # Read consolidated content
        try:
            summary_content = summary_file.read_text(encoding='utf-8')
            raw_notes_content = raw_notes_file.read_text(encoding='utf-8')
            attachments_content = attachments_file.read_text(encoding='utf-8')
            
            # Verify each disassembled file's content is in consolidated files
            for base_name, files in disassembled_files.items():
                # Skip files that don't have summary or raw notes
                if not files['summary'] and not files['raw_notes']:
                    continue
                    
                # Check summary content
                if files['summary'] and files['summary'].exists():
                    summary_text = files['summary'].read_text(encoding='utf-8').strip()
                    if summary_text and summary_text not in summary_content:
                        self.errors.append(f"Summary content from {files['summary']} not found in consolidated Summary.md")
                        
                # Check raw notes content
                if files['raw_notes'] and files['raw_notes'].exists():
                    raw_notes_text = files['raw_notes'].read_text(encoding='utf-8').strip()
                    if raw_notes_text and raw_notes_text not in raw_notes_content:
                        self.errors.append(f"Raw notes content from {files['raw_notes']} not found in consolidated Raw Notes.md")
            
            # Verify all attachments from parse phase are in the attachments file
            for parent_dir, attachments in self.attachments.items():
                for attachment in attachments:
                    # Extract the attachment ID from the path
                    attachment_id = attachment['path'].stem.replace('.parsed', '')
                    # Get the attachment content
                    content = attachment['content'].strip()
                    
                    # Look for any attachment reference with this ID and any type
                    found_ref = False
                    for attachment_type in ['DOC', 'EXCEL', 'PDF', 'JSON', 'TXT', 'PNG', 'JPG', 'HEIC', 'SVG', 'IMAGE', 'OTHER']:
                        attachment_ref = f"[ATTACH:{attachment_type}:{attachment_id}]"
                        if attachment_ref in attachments_content:
                            found_ref = True
                            # Find the section containing this attachment
                            section_start = attachments_content.find(f"### {attachment_ref}")
                            if section_start == -1:
                                self.errors.append(f"Missing section for attachment {attachment_id} in consolidated Attachments.md")
                            else:
                                # Find the next section or end of file
                                next_section = attachments_content.find("\n### ", section_start + 1)
                                if next_section == -1:
                                    next_section = len(attachments_content)
                                # Get the section content
                                section_content = attachments_content[section_start:next_section].strip()
                                # Check that the section has a summary and raw notes, unless it's an error case
                                if "Error processing" not in content and "Warning: Encoding Issue" not in content and "<html" not in content:
                                    if "--==SUMMARY==--" not in section_content:
                                        self.errors.append(f"Missing summary section for attachment {attachment_id} in consolidated Attachments.md")
                                    if "--==RAW NOTES==--" not in section_content:
                                        self.errors.append(f"Missing raw notes section for attachment {attachment_id} in consolidated Attachments.md")
                            break
                            
                    if not found_ref:
                        self.errors.append(f"No attachment reference found for {attachment_id} in consolidated Attachments.md")
                        continue
                        
            return len(self.errors) == 0
            
        except Exception as e:
            self.errors.append(f"Error validating split phase: {str(e)}")
            return False

def main():
    """Main entry point."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Validate Nova pipeline phases")
    parser.add_argument("processing_dir", help="Path to processing directory")
    args = parser.parse_args()
    
    # Run validation
    validator = PipelineValidator(args.processing_dir)
    is_valid = validator.validate()
    
    # Exit with appropriate status
    sys.exit(0 if is_valid else 1)

if __name__ == "__main__":
    main() 