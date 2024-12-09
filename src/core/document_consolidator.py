import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import structlog

from src.core.config import ProcessingConfig
from src.core.exceptions import (
    ConsolidationError,
    ConversionError,
    MediaError,
    NovaError,
    ProcessingError,
)
from src.processors.attachment_processor import AttachmentProcessor
from src.processors.html_processor import HTMLProcessor
from src.processors.markdown_processor import MarkdownProcessor

logger = structlog.get_logger(__name__)


@dataclass
class ConsolidationResult:
    """Result of document consolidation."""

    content: str
    html_files: List[Path]
    consolidated_html: Path
    warnings: List[str]
    metadata: List[dict]


class DocumentConsolidator:
    """Consolidates multiple markdown documents into one."""

    def __init__(self, base_dir: Path, output_dir: Path, config: ProcessingConfig):
        """Initialize the consolidator."""
        self.base_dir = base_dir
        self.output_dir = output_dir
        self.config = config

        # Initialize processors
        self.markdown_processor = MarkdownProcessor(
            media_dir=config.media_dir,
            template_dir=config.template_dir,
            debug_dir=config.debug_dir,
            error_tolerance=config.error_tolerance,
        )

        self.html_processor = HTMLProcessor(
            media_dir=config.media_dir,
            debug_dir=config.debug_dir,
            error_tolerance=config.error_tolerance,
        )

        self.attachment_processor = AttachmentProcessor(
            media_dir=config.media_dir,
            debug_dir=config.debug_dir,
            error_tolerance=config.error_tolerance,
        )

        # Create output directories
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "html").mkdir(parents=True, exist_ok=True)
        (output_dir / "pdf").mkdir(parents=True, exist_ok=True)

        # Create debug directories if enabled
        if config.debug_dir:
            config.debug_dir.mkdir(parents=True, exist_ok=True)
            (config.debug_dir / "html").mkdir(parents=True, exist_ok=True)
            (config.debug_dir / "html" / "individual").mkdir(
                parents=True, exist_ok=True
            )
            (config.debug_dir / "attachments").mkdir(parents=True, exist_ok=True)
            (config.debug_dir / "media").mkdir(parents=True, exist_ok=True)

    def consolidate_documents(
        self, input_files: List[Path], title: str
    ) -> ConsolidationResult:
        """Consolidate markdown documents into HTML and PDF."""
        try:
            # Use debug directory for HTML files if available
            html_dir = (
                (self.config.debug_dir / "html")
                if self.config.debug_dir
                else (self.output_dir / "html")
            )
            html_dir.mkdir(parents=True, exist_ok=True)

            # Create individual files directory
            individual_dir = (
                (self.config.debug_dir / "html" / "individual")
                if self.config.debug_dir
                else (html_dir / "individual")
            )
            individual_dir.mkdir(parents=True, exist_ok=True)

            processed_files = []
            metadata_list = []
            warnings = []

            # Process each file
            for doc_path in input_files:
                try:
                    # Process markdown
                    with doc_path.open() as f:
                        content = f.read()

                    # Process markdown and get metadata
                    try:
                        result = self.markdown_processor.process_markdown(
                            content, doc_path
                        )
                        metadata_list.append(result.metadata)
                        warnings.extend(result.warnings)
                    except Exception as e:
                        raise ProcessingError(f"Failed to process markdown: {str(e)}")

                    # Convert to HTML
                    try:
                        html_file = self.html_processor.convert_to_html(
                            result.content, doc_path, individual_dir
                        )
                        processed_files.append(html_file)
                    except ConversionError as e:
                        raise ProcessingError(f"HTML conversion failed: {str(e)}")

                except Exception as e:
                    if self.config.error_tolerance == "strict":
                        if not isinstance(e, ProcessingError):
                            raise ProcessingError(
                                f"Failed to process {doc_path}: {str(e)}"
                            )
                        raise
                    warnings.append(f"Failed to process {doc_path}: {str(e)}")
                    logger.error(
                        "Failed to process document",
                        error=str(e),
                        document=str(doc_path),
                    )

            if not processed_files:
                raise ProcessingError("No files were successfully processed")

            # Consolidate HTML files
            try:
                consolidated_html = html_dir / "consolidated.html"
                self.html_processor.consolidate_html_files(
                    processed_files, consolidated_html
                )
            except ConsolidationError as e:
                raise ProcessingError(f"Failed to consolidate HTML files: {str(e)}")

            # Copy individual files to output directory
            output_html_dir = self.output_dir / "html"
            output_html_dir.mkdir(parents=True, exist_ok=True)

            for html_file in processed_files:
                try:
                    import shutil

                    target_file = output_html_dir / html_file.name
                    shutil.copy2(html_file, target_file)
                    logger.info(f"Copied HTML file to output: {target_file}")
                except Exception as e:
                    logger.error(f"Failed to copy HTML file {html_file.name}: {str(e)}")

            return ConsolidationResult(
                content=consolidated_html.read_text(),
                html_files=processed_files,
                consolidated_html=consolidated_html,
                warnings=warnings,
                metadata=metadata_list,
            )

        except Exception as e:
            logger.error("Consolidation failed", error=str(e))
            if not isinstance(e, NovaError):
                e = ProcessingError(f"Document consolidation failed: {str(e)}")

            return ConsolidationResult(
                content="",
                html_files=[],
                consolidated_html=Path(),
                warnings=[str(e)],
                metadata=[],
            )
        finally:
            # Cleanup
            self.cleanup()

    def cleanup(self) -> None:
        """Clean up temporary files."""
        try:
            # Clean up processors
            self.markdown_processor.cleanup()
        except Exception as e:
            logger.error(f"Failed to cleanup: {str(e)}")
            if self.config.error_tolerance == "strict":
                raise
