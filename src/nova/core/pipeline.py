"""Pipeline module for Nova document processor."""

import warnings
from pathlib import Path
from typing import Dict, Any, Optional, List
from cryptography.utils import CryptographyDeprecationWarning
import os
import shutil

# Suppress warnings
warnings.filterwarnings('ignore', category=CryptographyDeprecationWarning)
warnings.filterwarnings('ignore', category=ResourceWarning, message='unclosed.*<ssl.SSLSocket.*>')

from .config import NovaConfig, MarkdownConfig, ImageConfig, OfficeConfig
from .state import StateManager
from .errors import NovaError, ProcessingError
from .logging import get_logger, create_progress, info, warning, error, success, path
from ..processors.markdown_processor import MarkdownProcessor
from ..processors.markdown_consolidate import MarkdownConsolidateProcessor
from ..processors.image_processor import ImageProcessor
from ..processors.office_processor import OfficeProcessor
from ..processors.three_file_split_processor import ThreeFileSplitProcessor

class Pipeline:
    """Main processing pipeline."""
    
    def __init__(self, config: 'NovaConfig'):
        """Initialize pipeline.
        
        Args:
            config: Nova configuration
        """
        self.config = config
        self.logger = get_logger(__name__)
        
        # Initialize state manager
        self.state = StateManager(self.config.paths.state_dir)
        
        # Initialize processors with their specific configs
        self.processors = {
            'markdown': MarkdownProcessor(
                processor_config=self.config.processors['markdown'],
                nova_config=self.config
            ),
            'markdown_consolidate': MarkdownConsolidateProcessor(
                processor_config=self.config.processors['markdown'],
                nova_config=self.config
            ),
            'image': ImageProcessor(
                processor_config=self.config.processors['image'],
                nova_config=self.config
            ),
            'office': OfficeProcessor(
                processor_config=self.config.processors['office'],
                nova_config=self.config
            ),
            'three_file_split': ThreeFileSplitProcessor(
                processor_config=self.config.processors['three_file_split'],
                nova_config=self.config
            )
        }
        
    def process(self) -> None:
        """Run the processing pipeline."""
        try:
            info("Starting pipeline processing...")
            
            # Phase 1: MARKDOWN_PARSE
            if self.config.processors['markdown'].enabled:
                info("Starting MARKDOWN_PARSE phase...")
                self._run_markdown_parse_phase()
            
            # Phase 2: MARKDOWN_CONSOLIDATE
            if self.config.processors['markdown'].enabled:
                info("Starting MARKDOWN_CONSOLIDATE phase...")
                self._run_markdown_consolidate_phase()
            
            # Phase 3: MARKDOWN_AGGREGATE
            if self.config.processors['markdown'].enabled:
                info("Starting MARKDOWN_AGGREGATE phase...")
                self._run_markdown_aggregate_phase()
            
            # Phase 4: MARKDOWN_SPLIT_THREEFILES
            if self.config.processors['three_file_split'].enabled:
                info("Starting MARKDOWN_SPLIT_THREEFILES phase...")
                self._run_markdown_split_phase()
            
            success("Pipeline processing complete")
            
        except Exception as e:
            error(f"Pipeline processing failed: {e}")
            raise ProcessingError(f"Pipeline processing failed: {str(e)}") from e

    def _run_markdown_parse_phase(self) -> None:
        """Run the markdown parse phase."""
        input_dir = Path(self.config.paths.input_dir)
        output_dir = Path(self.config.paths.phase_dirs['markdown_parse'])
        state_dir = self.config.paths.state_dir / 'markdown_parse'
        
        # Create phase directories
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Process markdown files
        with create_progress() as progress:
            for ext in self.config.processors['markdown'].extensions:
                files = list(input_dir.glob(f'**/*{ext}'))
                task = progress.add_task(f"Processing {ext} files", total=len(files))
                
                for md_file in files:
                    try:
                        # Get relative path but exclude phase directory names to prevent nesting
                        relative_path = md_file.relative_to(input_dir)
                        
                        # Skip if path contains phase directory names or is in a phase directory
                        if any(part in str(relative_path).lower() for part in ['markdown_parse', 'markdown_consolidate', 'phases']):
                            progress.console.print(f"[detail]Skipping file in phase directory: {md_file}[/]")
                            continue
                            
                        output_path = output_dir / relative_path
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Process the file and its attachments
                        self.processors['markdown'].process(md_file, output_path)
                        
                        # Update state
                        self.state.update_file_state(
                            phase='markdown_parse',
                            file_path=str(relative_path),
                            status='completed'
                        )
                        
                        progress.advance(task)
                        
                    except Exception as e:
                        error(f"Failed to process {md_file}: {e}")
                        self.state.update_file_state(
                            phase='markdown_parse',
                            file_path=str(relative_path),
                            status='failed',
                            error=str(e)
                        )

    def _run_markdown_consolidate_phase(self) -> None:
        """Run the markdown consolidate phase."""
        input_dir = Path(self.config.paths.phase_dirs['markdown_parse'])
        output_dir = Path(self.config.paths.phase_dirs['markdown_consolidate'])
        state_dir = Path(self.config.paths.state_dir) / 'markdown_consolidate'
        
        # Create phase directories
        output_dir.mkdir(parents=True, exist_ok=True)
        state_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Get all markdown files from previous phase
            input_files = []
            for ext in self.config.processors['markdown'].extensions:
                input_files.extend(input_dir.glob(f'**/*{ext}'))
            
            if not input_files:
                warning("No markdown files found for consolidation")
                return
            
            # Filter out attachments (files in a directory named after another markdown file)
            main_files = []
            for input_file in input_files:
                # Skip if this is an attachment (in a directory with same name as a markdown file)
                if input_file.parent.name == input_file.parent.parent.stem:
                    continue
                main_files.append(input_file)
            
            with create_progress() as progress:
                task = progress.add_task("Consolidating markdown files", total=len(main_files))
                
                for input_file in main_files:
                    try:
                        # Get the output path - always in root of output directory
                        output_path = output_dir / input_file.name
                        
                        # Process the file and its attachments
                        self.processors['markdown_consolidate'].process(input_file, output_path)
                        
                        # Update state
                        self.state.update_file_state(
                            phase='markdown_consolidate',
                            file_path=str(input_file.relative_to(input_dir)),
                            status='completed'
                        )
                        
                        progress.advance(task)
                        
                    except Exception as e:
                        error(f"Failed to consolidate {input_file}: {e}")
                        self.state.update_file_state(
                            phase='markdown_consolidate',
                            file_path=str(input_file.relative_to(input_dir)),
                            status='failed',
                            error=str(e)
                        )
                        
        except Exception as e:
            error(f"Failed to run markdown consolidate phase: {e}")
            self.state.update_file_state(
                phase='markdown_consolidate',
                file_path='consolidation',
                status='failed',
                error=str(e)
            )

    def _run_markdown_aggregate_phase(self) -> None:
        """
        Run the markdown aggregate phase, merging all consolidated markdown files
        into a single markdown file.
        """
        input_dir = Path(self.config.paths.phase_dirs['markdown_consolidate'])
        output_dir = Path(self.config.paths.phase_dirs['markdown_aggregate'])
        state_dir = Path(self.config.paths.state_dir) / 'markdown_aggregate'

        # Create phase directories
        output_dir.mkdir(parents=True, exist_ok=True)
        state_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Gather all markdown files
            input_files = []
            for ext in self.config.processors['markdown'].extensions:
                input_files.extend(input_dir.glob(f'**/*{ext}'))

            if not input_files:
                warning("No markdown files found for aggregation")
                return

            # Single output file
            output_filename = self.config.processors['markdown'].aggregate['output_filename']
            merged_output_path = output_dir / output_filename

            with merged_output_path.open("w", encoding="utf-8") as merged_output:
                # Add summary marker and header
                merged_output.write("--==SUMMARY==--\n\n")
                merged_output.write("# Summary\n\n")

                # Write summary content
                for md_file in input_files:
                    try:
                        rel_path = md_file.relative_to(input_dir)
                        with md_file.open("r", encoding="utf-8") as f:
                            file_content = f.read()
                            
                            # Add file header
                            if self.config.processors['markdown'].aggregate['include_file_headers']:
                                merged_output.write(f"## Start of file: {rel_path}\n\n")
                            
                            # Write content up to raw notes marker
                            raw_notes_marker = "--==RAW NOTES==--"
                            if raw_notes_marker in file_content:
                                summary_content = file_content.split(raw_notes_marker)[0].strip()
                                merged_output.write(summary_content)
                            else:
                                merged_output.write(file_content)
                            
                            # Add file footer
                            if self.config.processors['markdown'].aggregate['include_file_headers']:
                                merged_output.write(f"\n\n## End of file: {rel_path}\n")
                            
                            # Add separator between files
                            if self.config.processors['markdown'].aggregate['add_separators']:
                                merged_output.write("\n\n---\n\n")
                    except Exception as e:
                        error(f"Failed to process summary for {md_file}: {e}")
                        self.state.update_file_state(
                            phase='markdown_aggregate',
                            file_path=str(rel_path),
                            status='failed',
                            error=str(e)
                        )

                # Add raw notes marker and header
                merged_output.write("\n\n--==RAW NOTES==--\n\n")
                merged_output.write("# Raw Notes\n\n")

                # Write raw notes content
                for md_file in input_files:
                    try:
                        rel_path = md_file.relative_to(input_dir)
                        with md_file.open("r", encoding="utf-8") as f:
                            file_content = f.read()
                            
                            # Add file header
                            if self.config.processors['markdown'].aggregate['include_file_headers']:
                                merged_output.write(f"## Start of file: {rel_path}\n\n")
                            
                            # Write content after raw notes marker
                            raw_notes_marker = "--==RAW NOTES==--"
                            if raw_notes_marker in file_content:
                                raw_notes_content = file_content.split(raw_notes_marker)[1].strip()
                                merged_output.write(raw_notes_content)
                            
                            # Add file footer
                            if self.config.processors['markdown'].aggregate['include_file_headers']:
                                merged_output.write(f"\n\n## End of file: {rel_path}\n")
                            
                            # Add separator between files
                            if self.config.processors['markdown'].aggregate['add_separators']:
                                merged_output.write("\n\n---\n\n")

                        self.state.update_file_state(
                            phase='markdown_aggregate',
                            file_path=str(rel_path),
                            status='completed'
                        )
                        
                    except Exception as e:
                        error(f"Failed to process raw notes for {md_file}: {e}")
                        self.state.update_file_state(
                            phase='markdown_aggregate',
                            file_path=str(rel_path),
                            status='failed',
                            error=str(e)
                        )

                # Add attachments marker and header
                merged_output.write("\n\n--==ATTACHMENTS==--\n\n")
                merged_output.write("# File Attachments\n\n")
                
                info(f"All markdown files merged into {merged_output_path}")
                
        except Exception as e:
            error(f"Failed to run markdown aggregate phase: {e}")
            self.state.update_file_state(
                phase='markdown_aggregate',
                file_path='aggregation',
                status='failed',
                error=str(e)
            )

    def _run_markdown_split_phase(self) -> None:
        """Run the markdown split phase."""
        input_path = Path(self.config.paths.phase_dirs['markdown_aggregate']) / self.config.processors['markdown'].aggregate['output_filename']
        output_dir = Path(self.config.paths.phase_dirs['markdown_split'])
        state_dir = Path(self.config.paths.state_dir) / 'markdown_split'
        
        # Create phase directories
        output_dir.mkdir(parents=True, exist_ok=True)
        state_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            if not input_path.exists():
                warning("No aggregated markdown file found for splitting")
                return
            
            # Process the aggregated file
            self.processors['three_file_split'].process(input_path, output_dir)
            
            # Update state
            self.state.update_file_state(
                phase='markdown_split',
                file_path=str(input_path.name),
                status='completed'
            )
            
            info(f"Split markdown files created in {output_dir}")
            
        except Exception as e:
            error(f"Failed to run markdown split phase: {e}")
            self.state.update_file_state(
                phase='markdown_split',
                file_path=str(input_path.name),
                status='failed',
                error=str(e)
            )

    def _handle_binary_file(self, file_path: Path) -> None:
        """Handle a binary file by moving it to the appropriate processing directory and creating markdown representation.
        
        Args:
            file_path: Path to the binary file
            
        Returns:
            Optional[Path]: Path to the markdown representation if created
        """
        # Get relative path from input directory to maintain structure
        rel_path = file_path.relative_to(Path(os.getenv('NOVA_INPUT_DIR')))
        
        # Determine the appropriate directory based on file type
        suffix = file_path.suffix.lower()
        
        if suffix in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.heic', '.webp'}:
            # Image files go to images/original and processed
            original_dir = Path(os.getenv('NOVA_ORIGINAL_IMAGES_DIR'))
            processed_dir = Path(os.getenv('NOVA_PROCESSED_IMAGES_DIR'))
            
            # Create output directories with parent structure
            original_path = original_dir / rel_path
            processed_path = processed_dir / rel_path
            original_path.parent.mkdir(parents=True, exist_ok=True)
            processed_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy to original directory
            shutil.copy2(file_path, original_path)
            
            # Process image
            try:
                self.image_processor.process(original_path, processed_path)
                logger.info(f"Processed image {file_path} to {processed_path}")
            except Exception as e:
                logger.error(f"Failed to process image {file_path}: {e}")
                
        elif suffix in {'.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.pdf'}:
            # Office documents go to office/assets
            target_dir = Path(os.getenv('NOVA_OFFICE_ASSETS_DIR'))
            
            # Create output directory with parent structure
            target_path = target_dir / rel_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy to assets directory
            shutil.copy2(file_path, target_path)
            
            try:
                # Create markdown representation in markdown_parse directory
                markdown_dir = Path(os.getenv('NOVA_PHASE_MARKDOWN_PARSE'))
                markdown_path = markdown_dir / rel_path.parent / (file_path.stem + '.md')
                markdown_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Convert to markdown using markdown handler
                content = self.markdown_handler.convert_document(target_path, markdown_path)
                with open(markdown_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"Created markdown representation at {markdown_path}")
                
            except Exception as e:
                logger.error(f"Failed to convert office document {file_path}: {e}")
        else:
            # Other binary files are not processed
            logger.warning(f"Skipping unsupported binary file: {file_path}")
            return