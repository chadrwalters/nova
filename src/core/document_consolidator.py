"""Document consolidation functionality."""

import os
from pathlib import Path
from typing import List, Optional

import structlog

from src.core.exceptions import ProcessingError
from src.processors.html_processor import HTMLProcessor
from src.processors.markdown_processor import MarkdownProcessor
from src.core.logging import get_file_logger, log_file_operation
from src.core.config import ProcessingConfig

logger = structlog.get_logger(__name__)


class DocumentConsolidator:
    """Handles consolidation of multiple documents into a single output."""

    def __init__(
        self,
        config: ProcessingConfig,
        error_tolerance: bool = False,
    ) -> None:
        """Initialize the document consolidator.

        Args:
            config: Processing configuration
            error_tolerance: Whether to continue on errors
        """
        self.config = config
        self.error_tolerance = error_tolerance
        self.logger = get_file_logger(__name__)

        # Initialize processors
        self.markdown_processor = MarkdownProcessor(
            temp_dir=self.config.temp_dir,
            media_dir=self.config.media_dir,
            error_tolerance=error_tolerance
        )
        self.html_processor = HTMLProcessor(
            temp_dir=self.config.temp_dir,
            template_dir=Path("src/resources/templates"),
            error_tolerance=error_tolerance
        )

        # Create all processing directories
        for dir_path in [
            self.config.html_dir,
            self.config.temp_dir,
            self.config.media_dir,
            self.config.attachments_dir,
            self.config.consolidated_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)
            log_file_operation(self.logger, "create", dir_path, "directory")

    def consolidate_files(self, files: List[Path]) -> None:
        """Consolidate multiple files into a single output."""
        try:
            # Process each file
            processed_contents = []
            
            for i, file_path in enumerate(files, 1):
                self.logger.info(f"Processing file {i}/{len(files)}", path=str(file_path))
                
                # Process markdown
                content = self._process_file(file_path)
                processed_contents.append(content)
                
                # Save individual HTML
                html_path = self.config.html_dir / file_path.with_suffix('.html').name
                self.html_processor.convert_to_html(content, html_path)
                log_file_operation(self.logger, "create", html_path, "html")

            # Create consolidated markdown
            consolidated_md = "\n\n".join(processed_contents)
            md_path = self.config.consolidated_dir / "consolidated.md"
            md_path.write_text(consolidated_md, encoding="utf-8")
            log_file_operation(self.logger, "create", md_path, "markdown")

            # Create consolidated HTML
            html_path = self.config.consolidated_dir / "consolidated.html"
            self.html_processor.convert_to_html(consolidated_md, html_path)
            log_file_operation(self.logger, "create", html_path, "html")

            # Generate PDF
            pdf_path = self.config.output_dir / "consolidated.pdf"
            self.html_processor.generate_pdf(
                html_path.read_text(encoding="utf-8"), 
                pdf_path
            )
            log_file_operation(self.logger, "create", pdf_path, "pdf")

        except Exception as err:
            self.logger.error("Consolidation failed", exc_info=err)
            if not self.error_tolerance:
                raise ProcessingError(f"Error consolidating files: {err}") from err

    def _process_file(self, file_path: Path) -> str:
        """Process a single markdown file.

        Args:
            file_path: Path to the markdown file

        Returns:
            Processed markdown content
        """
        try:
            # Read file content
            self.logger.info(f"Reading content from: {file_path}")
            content = file_path.read_text(encoding="utf-8")
            self.logger.info(f"Successfully read {len(content)} characters from {file_path}")

            # Process content
            self.logger.info(f"Processing content from {file_path}")
            processed = self.markdown_processor.process_content(content)
            if processed:
                self.logger.info(
                    f"Successfully processed {file_path}, output length: {len(processed)}"
                )
                return processed
            else:
                self.logger.warning(f"Failed to process {file_path}")
                if not self.error_tolerance:
                    raise ProcessingError(f"Failed to process {file_path}")

            self.logger.info(f"Processed markdown file: {file_path}")

            return ""

        except Exception as err:
            if self.error_tolerance:
                self.logger.warning(f"Error processing file {file_path}: {err}")
                return ""
            raise ProcessingError(f"Error processing file {file_path}: {err}") from err
