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
from ..processors.image_processor import ImageProcessor
from ..processors.office_processor import OfficeProcessor
from ..processors.components.markdown_handlers import ConsolidationHandler

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
            'image': ImageProcessor(
                processor_config=self.config.processors['image'],
                nova_config=self.config
            ),
            'office': OfficeProcessor(
                processor_config=self.config.processors['office'],
                nova_config=self.config
            )
        }
        
        # Initialize consolidation handler
        self.consolidation_handler = ConsolidationHandler(
            processor_config=self.config.processors['markdown'],
            nova_config=self.config
        )
        
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
            
            # Group files by type/category based on filename pattern
            journal_files = [f for f in input_files if 'Journal' in f.stem]
            other_files = [f for f in input_files if 'Journal' not in f.stem]
            
            with create_progress() as progress:
                # Consolidate journal entries
                if journal_files:
                    task = progress.add_task("Consolidating journal entries", total=1)
                    journal_output = output_dir / 'consolidated_journal.md'
                    self.consolidation_handler.consolidate_markdown(journal_files, journal_output)
                    self.state.update_file_state(
                        phase='markdown_consolidate',
                        file_path='consolidated_journal.md',
                        status='completed'
                    )
                    progress.advance(task)
                
                # Consolidate other files
                if other_files:
                    task = progress.add_task("Consolidating other documents", total=1)
                    other_output = output_dir / 'consolidated_documents.md'
                    self.consolidation_handler.consolidate_markdown(other_files, other_output)
                    self.state.update_file_state(
                        phase='markdown_consolidate',
                        file_path='consolidated_documents.md',
                        status='completed'
                    )
                    progress.advance(task)
            
        except Exception as e:
            error(f"Failed to consolidate markdown: {e}")
            self.state.update_file_state(
                phase='markdown_consolidate',
                file_path='consolidation',
                status='failed',
                error=str(e)
            )