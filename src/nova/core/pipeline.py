"""Pipeline module for Nova document processor."""

import warnings
from pathlib import Path
from typing import Dict, Any, Optional, List
from cryptography.utils import CryptographyDeprecationWarning
import os
import shutil
import re
import tempfile
import logging

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
        
        # Configure logging
        self.logger = get_logger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Add console handler for debug messages
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
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
        
        self.logger.debug("Pipeline initialized with debug logging enabled")
        
    @staticmethod
    def _sanitize_path(path_str: str) -> str:
        """Sanitize a path string to handle data URIs and other problematic paths."""
        # Check if this is a data URI path
        if 'data:' in path_str:
            # Extract the part before data: if it exists
            parts = path_str.split('data:', 1)
            base_path = parts[0].strip()
            if base_path:
                return base_path
            
            # If no base path, generate a safe name
            return f"embedded_content_{hash(path_str) & 0xFFFFFFFF}.md"
        
        return path_str

    def _create_temp_file(self, original_path: str, content: str = "") -> Path:
        """Create a temporary file with a safe name.
        
        Args:
            original_path: Original path string
            content: Optional content to write to the file
            
        Returns:
            Path to the temporary file
        """
        # Create a temporary file with a safe name
        temp_dir = Path(tempfile.gettempdir())
        safe_name = f"nova_temp_{hash(original_path) & 0xFFFFFFFF}.md"
        temp_path = temp_dir / safe_name
        
        # Write content if provided
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return temp_path

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
        
        # Log directory information
        self.logger.debug(f"Input directory: {input_dir}")
        self.logger.debug(f"Output directory: {output_dir}")
        self.logger.debug(f"State directory: {state_dir}")
        
        # Process markdown files
        with create_progress() as progress:
            for ext in self.config.processors['markdown'].extensions:
                try:
                    self.logger.debug(f"Processing files with extension: {ext}")
                    
                    # Get list of files safely
                    file_paths = []
                    glob_pattern = f'**/*{ext}'
                    self.logger.debug(f"Searching with glob pattern: {glob_pattern}")
                    
                    for file_path in input_dir.glob(glob_pattern):
                        try:
                            # Convert to string and check for data URI
                            path_str = str(file_path)
                            self.logger.debug(f"Found file: {path_str}")
                            
                            if 'data:' in path_str:
                                self.logger.debug("File path contains data URI")
                                # Extract the actual path part
                                base_path = path_str.split('data:', 1)[0].strip()
                                if base_path:
                                    self.logger.debug(f"Using base path: {base_path}")
                                    file_paths.append(base_path)
                                else:
                                    # Generate a safe name in the input directory
                                    safe_name = f"embedded_content_{hash(path_str) & 0xFFFFFFFF}.md"
                                    safe_path = input_dir / safe_name
                                    self.logger.debug(f"Generated safe path: {safe_path}")
                                    file_paths.append(str(safe_path))
                            else:
                                self.logger.debug(f"Using original path: {path_str}")
                                file_paths.append(path_str)
                        except Exception as e:
                            error(f"Failed to process path: {e}")
                            self.logger.debug(f"Path processing error details: {str(e)}", exc_info=True)
                            continue
                    
                    self.logger.debug(f"Found {len(file_paths)} files to process")
                    task = progress.add_task(f"Processing {ext} files", total=len(file_paths))
                    
                    for file_path in file_paths:
                        try:
                            self.logger.debug(f"Processing file: {file_path}")
                            # Create Path object from sanitized path
                            md_file = Path(file_path)
                            self.logger.debug(f"Created Path object: {md_file}")
                            
                            # Get relative path but exclude phase directory names to prevent nesting
                            try:
                                relative_path = md_file.relative_to(input_dir)
                                self.logger.debug(f"Relative path: {relative_path}")
                            except ValueError:
                                # If we can't get relative path, use a safe name in root
                                relative_path = Path(f"embedded_content_{hash(file_path) & 0xFFFFFFFF}.md")
                                self.logger.debug(f"Using generated relative path: {relative_path}")
                            
                            # Skip if path contains phase directory names or is in a phase directory
                            if any(part in str(relative_path).lower() for part in ['markdown_parse', 'markdown_consolidate', 'phases']):
                                self.logger.debug(f"Skipping file in phase directory: {md_file}")
                                progress.console.print(f"[detail]Skipping file in phase directory: {md_file}[/]")
                                continue
                                
                            output_path = output_dir / relative_path
                            self.logger.debug(f"Output path: {output_path}")
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            
                            # Process the file
                            self.logger.debug(f"Processing file with markdown processor: {md_file} -> {output_path}")
                            self.processors['markdown'].process(md_file, output_path)
                            
                            # Update state
                            self.logger.debug(f"Updating state for: {relative_path}")
                            self.state.update_file_state(
                                phase='markdown_parse',
                                file_path=str(relative_path),
                                status='completed'
                            )
                            
                            progress.advance(task)
                            
                        except Exception as e:
                            error(f"Failed to process {file_path}: {e}")
                            self.logger.debug(f"File processing error details: {str(e)}", exc_info=True)
                            self.state.update_file_state(
                                phase='markdown_parse',
                                file_path=str(relative_path) if 'relative_path' in locals() else str(file_path),
                                status='failed',
                                error=str(e)
                            )
                            
                except Exception as e:
                    error(f"Failed to process {ext} files: {e}")
                    self.logger.debug(f"Extension processing error details: {str(e)}", exc_info=True)
                    continue

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

            # Track content for proper distribution
            summary_content = []
            raw_notes_content = []
            attachments_content = []
            total_content_size = 0

            # Process each file
            for md_file in input_files:
                try:
                    rel_path = md_file.relative_to(input_dir)
                    with md_file.open("r", encoding="utf-8") as f:
                        file_content = f.read()
                        total_content_size += len(file_content.encode('utf-8'))

                        # Add file header
                        if self.config.processors['markdown'].aggregate['include_file_headers']:
                            header = f"## Start of file: {rel_path}\n\n"
                            file_content = header + file_content

                        # Add to appropriate section
                        if '--==SUMMARY==--' in file_content:
                            summary_content.append(file_content)
                        elif '--==RAW NOTES==--' in file_content:
                            raw_notes_content.append(file_content)
                        else:
                            raw_notes_content.append(file_content)

                        # Extract any attachment blocks
                        attachment_blocks = re.findall(r'--==ATTACHMENT_BLOCK: (.+?)==--.*?--==ATTACHMENT_BLOCK_END==--', 
                                                     file_content, re.DOTALL)
                        if attachment_blocks:
                            attachments_content.extend(attachment_blocks)

                except Exception as e:
                    error(f"Failed to process file {md_file}: {str(e)}")
                    continue

            # Single output file
            output_filename = self.config.processors['markdown'].aggregate['output_filename']
            merged_output_path = output_dir / output_filename

            with merged_output_path.open("w", encoding="utf-8") as merged_output:
                # Write summary section
                merged_output.write("# Summary\n\n")
                for content in summary_content:
                    # Remove any existing summary headers
                    content = re.sub(r'^#\s*Summary\s*$', '', content, flags=re.MULTILINE)
                    merged_output.write(content)
                    if self.config.processors['markdown'].aggregate['add_separators']:
                        merged_output.write("\n\n---\n\n")

                # Write raw notes section
                merged_output.write("\n\n# Raw Notes\n\n")
                for content in raw_notes_content:
                    # Remove any existing raw notes headers
                    content = re.sub(r'^#\s*Raw\s*Notes\s*$', '', content, flags=re.MULTILINE)
                    merged_output.write(content)
                    if self.config.processors['markdown'].aggregate['add_separators']:
                        merged_output.write("\n\n---\n\n")

                # Write attachments section
                merged_output.write("\n\n# File Attachments\n\n")
                if attachments_content:
                    merged_output.write("\n".join(sorted(set(attachments_content))))
                    merged_output.write("\n")

            info(f"All markdown files merged into {merged_output_path}")
            
            # Validate content distribution
            output_size = merged_output_path.stat().st_size
            if abs(output_size - total_content_size) > total_content_size * 0.1:
                warning(f"Significant content size difference: Input={total_content_size}, Output={output_size}")

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
            
            # Read content from input file
            with input_path.open('r', encoding='utf-8') as f:
                content = f.read()
            
            # Set up output files
            output_files = {
                'summary': output_dir / 'summary.md',
                'raw_notes': output_dir / 'raw_notes.md',
                'attachments': output_dir / 'attachments.md'
            }
            
            # Process the content
            self.processors['three_file_split'].process(content, output_files)
            
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