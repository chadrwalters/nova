"""Document consolidation functionality."""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any, Sequence
import asyncio
from dataclasses import dataclass, field
import shutil

import structlog
import aiofiles

from src.core.exceptions import ProcessingError
from src.processors.html_processor import HTMLProcessor
from src.processors.markdown_processor import MarkdownProcessor
from src.core.logging import get_file_logger, log_file_operation
from src.core.resource_manager import ResourceManager, ResourceLimits
from src.core.validation import validate_markdown_file, ValidationResult
from src.core.exceptions import ConsolidationError
from src.processors.pdf_processor import PDFAttachmentHandler

logger = structlog.get_logger(__name__)

@dataclass
class ConsolidationState:
    """State tracking for document consolidation."""
    current_file: Optional[Path] = None
    processed_files: set[Path] = field(default_factory=set)
    failed_files: dict[Path, str] = field(default_factory=dict)
    validation_results: dict[Path, ValidationResult] = field(default_factory=dict)
    pdf_attachments: dict[str, Path] = field(default_factory=dict)

class DocumentConsolidator:
    """Handles document consolidation with robust error handling and resource management."""

    def __init__(
        self,
        processing_dir: Path,
        error_tolerance: bool = False,
        retry_count: int = 3
    ) -> None:
        """Initialize document consolidator.

        Args:
            processing_dir: Directory for processing files
            error_tolerance: Whether to continue on non-critical errors
            retry_count: Number of retries for failed operations
        """
        self.processing_dir = processing_dir
        self.error_tolerance = error_tolerance
        self.retry_count = retry_count
        self.logger = logger
        
        # Initialize state and managers
        self.state = ConsolidationState()
        self.resource_manager = ResourceManager()
        
        # Initialize processors
        self.markdown_processor = MarkdownProcessor(
            temp_dir=processing_dir / "temp",
            media_dir=processing_dir / "media",
            error_tolerance=error_tolerance
        )
        
        # Find wkhtmltopdf path
        wkhtmltopdf_path = shutil.which('wkhtmltopdf')
        if not wkhtmltopdf_path:
            raise ProcessingError("wkhtmltopdf not found in system PATH")
        
        self.html_processor = HTMLProcessor(
            temp_dir=processing_dir / "temp",
            wkhtmltopdf_path=wkhtmltopdf_path
        )
        
        self.pdf_handler = PDFAttachmentHandler(processing_dir)
        
        # Create required directories
        (processing_dir / "temp").mkdir(parents=True, exist_ok=True)
        (processing_dir / "media").mkdir(parents=True, exist_ok=True)

    def consolidate_files(self, input_files: Sequence[Path], output_file: Optional[Path] = None) -> Path:
        """Consolidate multiple markdown files into a single PDF.

        Args:
            input_files: Sequence of input markdown file paths
            output_file: Optional output file path. If not provided, will use processing_dir/consolidated.pdf

        Returns:
            Path to the consolidated PDF file

        Raises:
            ConsolidationError: If consolidation fails
        """
        try:
            # Create output file path
            if output_file is None:
                output_file = self.processing_dir / "consolidated.pdf"
            
            # Process files asynchronously
            asyncio.run(self.process_files(list(input_files), output_file))
            
            return output_file
            
        except Exception as e:
            self.logger.error(
                "Consolidation failed",
                error=str(e),
                input_files=len(input_files)
            )
            raise ConsolidationError(f"Failed to consolidate files: {e}")

    async def process_files(self, input_files: list[Path], output_file: Path) -> None:
        """Process input files and generate consolidated output.

        Args:
            input_files: List of input markdown files
            output_file: Output PDF file path

        Raises:
            ConsolidationError: If consolidation fails
        """
        try:
            # Track processed files
            self.state.processed_files = []
            self.state.pdf_attachments = {}
            consolidated_html = []

            # Process each file
            for input_file in input_files:
                self.logger.info(
                    "Processing file",
                    file=str(input_file)
                )

                # Process file with retries
                html_content = await self._process_file_with_retry(input_file)
                if html_content:
                    consolidated_html.append(html_content)
                    self.state.processed_files.append(input_file)

            if not consolidated_html:
                raise ConsolidationError("No files were successfully processed")

            # Write consolidated HTML to temporary file
            temp_html_file = self.processing_dir / "temp" / "consolidated.html"
            async with aiofiles.open(temp_html_file, 'w') as f:
                await f.write('\n'.join(consolidated_html))

            # Update PDF references in consolidated output
            if self.state.pdf_attachments:
                async with aiofiles.open(temp_html_file, 'r') as f:
                    content = await f.read()
                updated_content = self.pdf_handler.update_pdf_references(
                    content,
                    self.state.pdf_attachments
                )
                async with aiofiles.open(temp_html_file, 'w') as f:
                    await f.write(updated_content)

            # Generate PDF from HTML
            css_path = Path("src/resources/styles/pdf.css")
            async with aiofiles.open(temp_html_file, 'r') as f:
                html_content = await f.read()
                await self.html_processor.generate_pdf(
                    html_content,
                    output_file,
                    css_path
                )

        except Exception as e:
            raise ConsolidationError(f"Consolidation failed: {e}")

    async def _process_file_with_retry(self, input_file: Path) -> Optional[str]:
        """Process a single file with retries.

        Args:
            input_file: Input file path

        Returns:
            Processed HTML content or None if processing failed
        """
        retries = 0
        while retries < self.retry_count:
            try:
                # Process markdown
                processor = MarkdownProcessor(
                    self.processing_dir / "temp",
                    self.processing_dir / "media",
                    self.error_tolerance
                )
                html_content = await processor.convert_to_html(input_file)

                # Track PDF attachments
                async with aiofiles.open(input_file, 'r') as f:
                    content = await f.read()
                    pdf_attachments = await processor._find_pdf_attachments(content, input_file)
                    if pdf_attachments:
                        # Update paths to be relative to processing directory
                        updated_map = {}
                        for _, orig_path, proc_path in pdf_attachments:
                            # Make sure the processed path is relative to the processing directory
                            if proc_path.is_absolute():
                                try:
                                    proc_path = proc_path.relative_to(self.processing_dir)
                                except ValueError:
                                    # If it's not under processing directory, copy it there
                                    new_path = self.processing_dir / "attachments" / "pdf" / proc_path.name
                                    if not new_path.exists():
                                        shutil.copy2(proc_path, new_path)
                                    proc_path = new_path.relative_to(self.processing_dir)
                            updated_map[orig_path] = proc_path
                        self.state.pdf_attachments.update(updated_map)

                return html_content

            except Exception as e:
                retries += 1
                self.logger.warning(
                    "Processing retry",
                    file=str(input_file),
                    attempt=retries,
                    error=str(e)
                )
                await asyncio.sleep(1 * (2 ** (retries - 1)))  # Exponential backoff

        self.logger.error(
            "Processing failed after retries",
            file=str(input_file)
        )
        return None

    async def cleanup(self) -> None:
        """Clean up temporary files and resources."""
        try:
            # Clean up temporary files
            temp_dir = self.processing_dir / "temp"
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

            # Reset state
            self.state = ConsolidationState()

        except Exception as e:
            self.logger.error("Cleanup failed", error=str(e))
            if not self.error_tolerance:
                raise ConsolidationError(f"Cleanup failed: {e}")

    async def consolidate(self) -> None:
        """Consolidate markdown files into a single PDF."""
        try:
            # Process markdown files
            consolidated_markdown = await self._process_markdown_files()
            
            # Convert to HTML
            html_content = await self.html_processor.convert_markdown_to_html(consolidated_markdown)
            
            # Generate PDF
            output_file = self.output_dir / "consolidated.pdf"
            await self.html_processor.generate_pdf(html_content, output_file)
            
            # Verify the output
            if not output_file.exists():
                raise ProcessingError("PDF file was not generated")
                
            self.logger.info("Document consolidation complete",
                           output_file=str(output_file),
                           size=output_file.stat().st_size)
                           
        except Exception as e:
            self.logger.error("Document consolidation failed", error=str(e))
            raise ProcessingError(f"Failed to consolidate documents: {e}")
