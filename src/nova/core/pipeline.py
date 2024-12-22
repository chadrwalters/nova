"""Pipeline module for Nova document processor."""

import warnings
from pathlib import Path
from typing import Dict, Any, Optional, List
from cryptography.utils import CryptographyDeprecationWarning

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
            
            # Group files by their root directory
            file_groups = {}
            for input_file in input_files:
                # Get the root directory (either parent or grandparent)
                root_dir = input_file.parent
                if root_dir.name == input_file.stem:
                    # This is a file in its own directory, use parent as root
                    root_dir = root_dir.parent
                
                # Skip if this is an attachment (in a directory with same name as a markdown file)
                if root_dir.name == root_dir.parent.stem:
                    continue
                
                # Find the main file for this group
                main_file = None
                if input_file.parent.name == input_file.stem:
                    # This is the main file (directory named after it)
                    main_file = input_file
                elif input_file.parent == root_dir:
                    # This is a root-level file
                    # Check if there's a directory with the same name
                    potential_dir = root_dir / input_file.stem
                    if potential_dir.is_dir():
                        # This is a main file with attachments
                        main_file = input_file
                    else:
                        # This is a standalone file - check if it's referenced by another file
                        is_attachment = False
                        for other_file in input_files:
                            if other_file != input_file and other_file.stem == root_dir.name:
                                is_attachment = True
                                break
                        if not is_attachment:
                            # This is a standalone file not referenced by others
                            main_file = input_file
                
                if main_file:
                    # Use the root directory as the key for grouping
                    group_key = root_dir
                    if main_file.parent == root_dir:
                        # For standalone files, use their own name as the key
                        group_key = main_file.stem
                    
                    # Check if we already have a main file for this group
                    if group_key in file_groups:
                        # If both files have attachments, keep the one with more attachments
                        current_main = file_groups[group_key]
                        current_dir = current_main.parent / current_main.stem
                        new_dir = main_file.parent / main_file.stem
                        
                        if current_dir.is_dir() and new_dir.is_dir():
                            current_attachments = len(list(current_dir.glob('*.md')))
                            new_attachments = len(list(new_dir.glob('*.md')))
                            if new_attachments > current_attachments:
                                file_groups[group_key] = main_file
                        elif new_dir.is_dir():
                            # New file has attachments, old one doesn't
                            file_groups[group_key] = main_file
                    else:
                        file_groups[group_key] = main_file
            
            with create_progress() as progress:
                task = progress.add_task("Consolidating markdown files", total=len(file_groups))
                
                for root_dir, main_file in file_groups.items():
                    try:
                        # Get the output path - always in root of output directory
                        output_path = output_dir / main_file.name
                        
                        # Process the file and its attachments
                        self.processors['markdown_consolidate'].process(main_file, output_path)
                        
                        # Update state
                        self.state.update_file_state(
                            phase='markdown_consolidate',
                            file_path=str(main_file.relative_to(input_dir)),
                            status='completed'
                        )
                        
                        progress.advance(task)
                        
                    except Exception as e:
                        error(f"Failed to consolidate {main_file}: {e}")
                        self.state.update_file_state(
                            phase='markdown_consolidate',
                            file_path=str(main_file.relative_to(input_dir)),
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