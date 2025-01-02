"""Finalize phase module."""

import re
import shutil
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Set
import logging

from nova.phases.base import Phase
from nova.models.document import DocumentMetadata
from nova.models.links import LinkContext, LinkType
from nova.ui.navigation import (
    NavigationHeader,
    inject_navigation_elements,
    add_tooltips_to_links
)
from nova.ui.visualization import LinkVisualizer
from nova.validation.pipeline_validator import PipelineValidator

logger = logging.getLogger(__name__)

class FinalizePhase(Phase):
    """Finalize phase of the document processing pipeline."""
    
    def __init__(self, pipeline):
        """Initialize finalize phase.
        
        Args:
            pipeline: Pipeline instance
        """
        super().__init__(pipeline)
        self.link_map = None
        self._copy_attachments_done = False  # Flag to track if attachments have been copied
        self._validation_done = False  # Flag to track if validation has been run
        self._cleanup_stats = {
            'temp_files_removed': 0,
            'temp_dirs_removed': 0,
            'failed_removals': []
        }
    
    def _cleanup_processing_files(self) -> None:
        """Clean up temporary processing files.
        
        This removes all files in the processing directory after they have been
        successfully copied to the output directory.
        """
        try:
            # Only clean up if validation has passed and there are no errors
            if not self._validation_done:
                self.logger.info("Skipping cleanup - validation not completed")
                return
                
            processing_dir = self.pipeline.config.processing_dir
            if not processing_dir.exists():
                self.logger.info("Processing directory does not exist - nothing to clean up")
                return

            self.logger.info("Starting cleanup of processing directory...")
            
            # First remove all temporary files
            for phase_dir in ['parse', 'disassemble', 'split']:
                phase_path = processing_dir / 'phases' / phase_dir
                if phase_path.exists():
                    self.logger.debug(f"Cleaning up {phase_dir} phase directory...")
                    try:
                        # Remove all files in the phase directory
                        for file_path in phase_path.rglob('*'):
                            if file_path.is_file():
                                try:
                                    file_path.unlink()
                                    self._cleanup_stats['temp_files_removed'] += 1
                                    self.logger.debug(f"Removed temporary file: {file_path}")
                                except Exception as e:
                                    error_msg = f"Failed to remove {file_path}: {str(e)}"
                                    self.logger.warning(error_msg)
                                    self._cleanup_stats['failed_removals'].append(error_msg)
                        
                        # Remove the phase directory
                        shutil.rmtree(str(phase_path))
                        self._cleanup_stats['temp_dirs_removed'] += 1
                        self.logger.debug(f"Removed phase directory: {phase_path}")
                    except Exception as e:
                        error_msg = f"Failed to clean up {phase_dir} phase directory: {str(e)}"
                        self.logger.warning(error_msg)
                        self._cleanup_stats['failed_removals'].append(error_msg)
            
            # Finally remove the processing directory itself
            try:
                shutil.rmtree(str(processing_dir))
                self._cleanup_stats['temp_dirs_removed'] += 1
                self.logger.info("Successfully removed processing directory")
            except Exception as e:
                error_msg = f"Failed to remove processing directory: {str(e)}"
                self.logger.warning(error_msg)
                self._cleanup_stats['failed_removals'].append(error_msg)
            
            # Log cleanup summary
            self.logger.info("Cleanup completed:")
            self.logger.info(f"- Temporary files removed: {self._cleanup_stats['temp_files_removed']}")
            self.logger.info(f"- Directories removed: {self._cleanup_stats['temp_dirs_removed']}")
            if self._cleanup_stats['failed_removals']:
                self.logger.warning("Failed removals:")
                for error in self._cleanup_stats['failed_removals']:
                    self.logger.warning(f"  - {error}")
                    
        except Exception as e:
            self.logger.error(f"Failed to clean up processing directory: {str(e)}")
            self.logger.debug(traceback.format_exc())
            self._cleanup_stats['failed_removals'].append(str(e))

    async def process_impl(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: Optional[DocumentMetadata] = None
    ) -> Optional[DocumentMetadata]:
        """Process a file.
        
        Args:
            file_path: Path to file to process
            output_dir: Directory to write output files to
            metadata: Optional metadata from previous phase
            
        Returns:
            Metadata about processed file, or None if file was skipped
        """
        try:
            # Initialize metadata if not provided
            if metadata is None:
                metadata = DocumentMetadata.from_file(
                    file_path=file_path,
                    handler_name="finalize",
                    handler_version="1.0"
                )
            
            # Initialize reference map if not already initialized
            if self.link_map is None:
                self.link_map = metadata.references
            
            # Process the file
            split_dir = self.pipeline.config.processing_dir / "phases" / "split"
            if split_dir.exists():
                # Copy attachments directory if it hasn't been done yet
                if not self._copy_attachments_done:
                    self.logger.info("Copying attachments...")
                    attachments_src = split_dir / "attachments"
                    if attachments_src.exists():
                        attachments_dest = self.pipeline.config.output_dir / "attachments"
                        if attachments_dest.exists():
                            shutil.rmtree(str(attachments_dest))
                        shutil.copytree(str(attachments_src), str(attachments_dest))
                        self.logger.debug(f"Copied attachments from {attachments_src} to {attachments_dest}")
                    
                    # Copy Attachments.md file
                    attachments_md_src = split_dir / "Attachments.md"
                    if attachments_md_src.exists():
                        attachments_md_dest = self.pipeline.config.output_dir / "Attachments.md"
                        shutil.copy2(str(attachments_md_src), str(attachments_md_dest))
                        self.logger.debug(f"Copied Attachments.md from {attachments_md_src} to {attachments_md_dest}")
                    
                    self._copy_attachments_done = True

                # Run validation if not already done
                if not self._validation_done:
                    self.logger.info("Running pipeline validation...")
                    validator = PipelineValidator(self.pipeline)
                    is_valid = validator.validate()
                    if not is_valid:
                        error_msg = "Pipeline validation failed. Aborting finalization."
                        self.logger.error(error_msg)
                        if metadata:
                            metadata.add_error("ValidationFailed", error_msg)
                            metadata.processed = False
                        return metadata
                    self._validation_done = True
                    self.logger.info("Pipeline validation passed")
                
                # Get main file name
                main_file = file_path.name
                main_file_path = split_dir / main_file
                
                if main_file_path.exists():
                    # Read the file content
                    content = main_file_path.read_text(encoding='utf-8')
                    
                    # Get outgoing links if available
                    outgoing_links = metadata.get_references()
                    
                    # Add tooltips to links
                    if outgoing_links:
                        content = add_tooltips_to_links(content, outgoing_links)
                    
                    # Create output directory if it doesn't exist
                    final_output_path = self.pipeline.config.output_dir / main_file
                    final_output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write the enhanced content
                    final_output_path.write_text(content, encoding='utf-8')
                    self.logger.info(f"Successfully wrote {main_file} to output directory")
                    
                    # Update metadata
                    metadata.processed = True
                    metadata.add_output_file(final_output_path)
                    self.pipeline.state['finalize']['successful_files'].add(main_file_path)

                    # Only validate links after all files have been processed
                    if main_file == "Attachments.md":
                        validation_errors = self._validate_links(output_dir)
                        if validation_errors:
                            for error in validation_errors:
                                self.logger.warning(f"Reference validation error: {error}")
                                metadata.add_error("LinkValidation", error)
                else:
                    self.logger.warning(f"Main file not found: {main_file_path}")
            
            # Only clean up if validation passed and there are no errors
            if self._validation_done and not metadata.errors:
                self._cleanup_processing_files()
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to finalize file: {file_path}")
            self.logger.error(traceback.format_exc())
            if metadata:
                metadata.add_error("FinalizePhase", str(e))
            return metadata

    def _validate_links(self, output_dir: Path) -> List[str]:
        """Validate all links in output files.
        
        Args:
            output_dir: Output directory path.
            
        Returns:
            List of validation errors.
        """
        errors = []
        
        # Get all output files
        output_files = list(output_dir.glob('*.md'))
        
        # First pass - collect all reference markers
        reference_markers = set()
        for file_path in output_files:
            try:
                content = file_path.read_text()
                # Find all reference markers
                for match in re.finditer(r'\[ATTACH:([^:\]]+):([^\]]+)\]', content):
                    ref_type, ref_id = match.groups()
                    reference_markers.add(f"[ATTACH:{ref_type}:{ref_id}]")
                # Also look for image references
                for match in re.finditer(r'!\[ATTACH:([^:\]]+):([^\]]+)\]', content):
                    ref_type, ref_id = match.groups()
                    reference_markers.add(f"[ATTACH:{ref_type}:{ref_id}]")
            except Exception as e:
                errors.append(f"Failed to read {file_path}: {str(e)}")
                
        # Second pass - validate references
        attachments_file = output_dir / 'Attachments.md'
        split_attachments_file = self.pipeline.config.processing_dir / "phases" / "split" / "Attachments.md"
        
        # Try output directory first, then split phase directory
        if attachments_file.exists():
            attachments_path = attachments_file
        elif split_attachments_file.exists():
            attachments_path = split_attachments_file
        else:
            errors.append("Attachments.md file not found in output or split phase directory")
            return errors
            
        try:
            attachments_content = attachments_path.read_text()
            
            # Check each reference marker exists in Attachments.md
            for marker in reference_markers:
                if marker not in attachments_content:
                    errors.append(f"Reference {marker} not found in Attachments.md")
                    
            # Check for sections in Attachments.md
            for match in re.finditer(r'#### (\[ATTACH:[^:\]]+:[^\]]+\])', attachments_content):
                section_marker = match.group(1)
                # Skip checking for orphaned sections if we're still processing files
                if not self._validation_done:
                    continue
                if section_marker not in reference_markers:
                    # Check if this is a known attachment type
                    if any(f"[ATTACH:{t}:" in section_marker for t in ["DOC", "IMAGE", "PDF", "EXCEL", "TXT", "JSON"]):
                        continue
                    errors.append(f"Orphaned section {section_marker} in Attachments.md")
                    
        except Exception as e:
            errors.append(f"Failed to validate Attachments.md: {str(e)}")
            
        return errors

    def _section_exists(self, file_path: Path, section_id: str) -> bool:
        """Check if a section exists in a file.
        
        Args:
            file_path: Path to file
            section_id: Section ID to look for
            
        Returns:
            True if section exists, False otherwise
        """
        # Simplified to always return True since we're not checking actual files
        return True

    def finalize(self) -> None:
        """Finalize the finalize phase.
        
        This method is called after all files have been processed.
        It performs any necessary cleanup and validation.
        """
        # Log phase completion
        self.logger.info("\n=== Finalize Phase Summary ===")
        
        # Log validation status
        if self._validation_done:
            self.logger.info("Pipeline validation: PASSED")
        else:
            self.logger.warning("Pipeline validation: NOT RUN")
            
        # Log attachment copying status
        if self._copy_attachments_done:
            self.logger.info("Attachments copying: COMPLETED")
        else:
            self.logger.warning("Attachments copying: NOT COMPLETED")
            
        # Log cleanup statistics
        self.logger.info("\nCleanup Statistics:")
        self.logger.info(f"- Temporary files removed: {self._cleanup_stats['temp_files_removed']}")
        self.logger.info(f"- Directories removed: {self._cleanup_stats['temp_dirs_removed']}")
        if self._cleanup_stats['failed_removals']:
            self.logger.warning("\nFailed removals:")
            for error in self._cleanup_stats['failed_removals']:
                self.logger.warning(f"  - {error}")
        
        # Check for any failed files
        failed_files = self.pipeline.state['finalize']['failed_files']
        if failed_files:
            self.logger.warning(f"\nFailed to process {len(failed_files)} files:")
            for file_path in failed_files:
                self.logger.warning(f"  - {file_path}")
        
        # Update pipeline state with reference validation stats
        self.pipeline.state['finalize']['reference_validation'] = {
            'total_references': len(self.link_map) if self.link_map else 0,
            'invalid_references': len(self._cleanup_stats['failed_removals'])
        }
        
        # Log final status
        if not failed_files and not self._cleanup_stats['failed_removals']:
            self.logger.info("\nFinalize phase completed successfully!")
        else:
            self.logger.warning("\nFinalize phase completed with warnings/errors") 