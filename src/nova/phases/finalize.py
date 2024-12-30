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
            
            # Initialize link map if not already initialized
            if self.link_map is None:
                self.link_map = metadata.links
            
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
                    outgoing_links = metadata.get_outgoing_links()
                    
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
        """Validate links in a document.
        
        Args:
            metadata: Document metadata
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Get all outgoing links
        outgoing_links = metadata.get_outgoing_links()
        
        # Check each link
        for link in outgoing_links:
            # Check if target file exists
            target_path = Path(link.target_file)
            if not target_path.exists():
                errors.append(f"Broken link: {link.target_file} does not exist")
                continue
            
            # Check if target section exists (if specified)
            if link.target_section:
                if not self._section_exists(target_path, link.target_section):
                    errors.append(f"Broken link: Section {link.target_section} not found in {link.target_file}")
        
        return errors

    def _section_exists(self, file_path: Path, section_id: str) -> bool:
        """Check if a section exists in a file.
        
        Args:
            file_path: Path to file
            section_id: Section ID to look for
            
        Returns:
            True if section exists, False otherwise
        """
        try:
            content = file_path.read_text(encoding='utf-8')
            return f'<a id="{section_id}"></a>' in content
        except Exception:
            return False

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
        
        # Check link validation results
        if hasattr(self, 'link_map') and self.link_map:
            # Get overall link stats
            total_links = 0
            broken_links = 0
            repaired_links = 0
            
            # Count links in outgoing_links
            for links in self.link_map.outgoing_links.values():
                total_links += len(links)
                # Count broken links
                for link in links:
                    if not Path(link.target_file).exists():
                        broken_links += 1
            
            # Log link stats
            self.logger.info("Link validation summary:")
            self.logger.info(f"  Total links: {total_links}")
            self.logger.info(f"  Broken links: {broken_links}")
            self.logger.info(f"  Repaired links: {repaired_links}")
            
            # Update pipeline state
            self.pipeline.state['finalize']['link_validation'] = {
                'total_links': total_links,
                'broken_links': broken_links,
                'repaired_links': repaired_links
            } 