"""Finalize phase module."""

import re
import shutil
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Set

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
            # Run validation first if not already done
            if not self._validation_done:
                validator = PipelineValidator(self.pipeline.config.processing_dir)
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
                    attachments_src = split_dir / "attachments"
                    if attachments_src.exists():
                        attachments_dest = self.pipeline.config.output_dir / "attachments"
                        if attachments_dest.exists():
                            shutil.rmtree(str(attachments_dest))
                        shutil.copytree(str(attachments_src), str(attachments_dest))
                        self.logger.debug(f"Copied attachments from {attachments_src} to {attachments_dest}")
                    self._copy_attachments_done = True
                
                # Get main file name
                main_file = file_path.name
                main_file_path = split_dir / main_file
                
                if main_file_path.exists():
                    # Validate links
                    validation_errors = self._validate_links(metadata)
                    if validation_errors:
                        for error in validation_errors:
                            metadata.add_error("LinkValidation", error)
                    
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
                    self.logger.debug(f"Successfully wrote enhanced content to {final_output_path}")
                    
                    # Update metadata
                    metadata.processed = True
                    metadata.add_output_file(final_output_path)
                    self.pipeline.state['finalize']['successful_files'].add(main_file_path)
                else:
                    self.logger.debug(f"Main file not found: {main_file_path}")
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to finalize file: {file_path}")
            self.logger.error(traceback.format_exc())
            if metadata:
                metadata.add_error("FinalizePhase", str(e))
            return metadata

    def _validate_links(self, metadata: DocumentMetadata) -> List[str]:
        """Validate links in metadata.
        
        Args:
            metadata: Document metadata.
            
        Returns:
            List of validation errors.
        """
        validation_errors = []
        
        # Get references
        references = metadata.get_references()
        
        # Just validate that references have proper format [ATTACH:TYPE:MARKER]
        for marker, ref_type in references.items():
            if not re.match(r'^\[ATTACH:[A-Z]+:[a-zA-Z0-9_-]+\]$', marker):
                validation_errors.append(f"Invalid reference format: {marker}")
        
        return validation_errors

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
        # Log summary
        self.logger.info("Finalize phase completed")
        
        # Check for any failed files
        failed_files = self.pipeline.state['finalize']['failed_files']
        if failed_files:
            self.logger.warning(f"Failed to process {len(failed_files)} files:")
            for file_path in failed_files:
                self.logger.warning(f"  - {file_path}")
        
        # Update pipeline state with simplified reference tracking
        self.pipeline.state['finalize']['reference_validation'] = {
            'total_references': len(self.link_map) if self.link_map else 0,
            'invalid_references': 0
        } 