"""Document consolidation functionality."""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any, Sequence
import asyncio
from dataclasses import dataclass, field

import structlog
import aiofiles

from src.core.exceptions import ProcessingError
from src.processors.html_processor import HTMLProcessor
from src.processors.markdown_processor import MarkdownProcessor
from src.core.logging import get_file_logger, log_file_operation
from src.core.config import ProcessingConfig
from src.core.resource_manager import ResourceManager, ResourceLimits
from src.core.validation import validate_markdown_file, ValidationResult
from src.core.exceptions import ConsolidationError

logger = structlog.get_logger(__name__)

@dataclass
class ProcessingState:
    """Tracks the state of document processing."""
    current_file: Optional[Path] = None
    processed_files: set[Path] = field(default_factory=set)
    failed_files: dict[Path, str] = field(default_factory=dict)
    validation_results: dict[Path, ValidationResult] = field(default_factory=dict)

class DocumentConsolidator:
    """Handles document consolidation with robust error handling and resource management."""

    def __init__(
        self,
        config: ProcessingConfig,
        resource_limits: Optional[ResourceLimits] = None,
        error_tolerance: bool = False
    ):
        """Initialize the document consolidator.
        
        Args:
            config: Processing configuration
            resource_limits: Optional resource limits configuration
            error_tolerance: Whether to continue processing on non-critical errors
        """
        self.config = config
        self.resource_manager = ResourceManager(resource_limits)
        self.state = ProcessingState()
        self.retry_count = config.retry_count if hasattr(config, 'retry_count') else 3
        self.retry_delay = config.retry_delay if hasattr(config, 'retry_delay') else 1
        self.error_tolerance = error_tolerance
        self.logger = logger.bind(
            component="document_consolidator",
            error_tolerance=error_tolerance
        )
        
        # Create required directories
        os.makedirs(config.processing_dir / "temp", exist_ok=True)
        os.makedirs(config.processing_dir / "media", exist_ok=True)
        
        # Initialize processors with required directories
        self.markdown_processor = MarkdownProcessor(
            temp_dir=config.processing_dir / "temp",
            media_dir=config.processing_dir / "media"
        )
        self.html_processor = HTMLProcessor(
            temp_dir=config.processing_dir / "temp",
            template_dir=Path(__file__).parent.parent / "resources" / "templates"
        )

    def consolidate_files(self, input_files: Sequence[Path]) -> Path:
        """
        Consolidate multiple markdown files into a single PDF.

        Args:
            input_files: Sequence of input markdown file paths

        Returns:
            Path to the consolidated PDF file

        Raises:
            ConsolidationError: If consolidation fails
        """
        try:
            # Create output file path
            output_file = self.config.output_dir / "consolidated.pdf"
            
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
        """
        Processes multiple markdown files with error handling and state tracking.

        Args:
            input_files: List of input markdown files
            output_file: Output file path

        Raises:
            ConsolidationError: If processing fails
        """
        try:
            async with self.resource_manager.file_lock(output_file):
                consolidated_html = []
                
                for input_file in input_files:
                    self.state.current_file = input_file
                    
                    # Validate file
                    try:
                        validation_result = await validate_markdown_file(
                            input_file,
                            strict_hierarchy=False
                        )
                        self.state.validation_results[input_file] = validation_result
                    except Exception as e:
                        self.logger.error(
                            "Validation failed",
                            file=str(input_file),
                            error=str(e)
                        )
                        self.state.failed_files[input_file] = str(e)
                        if not self.error_tolerance:
                            raise ConsolidationError(f"Validation failed for {input_file}: {e}")
                        continue

                    # Process file with retries
                    html_content = await self._process_file_with_retry(input_file)
                    if html_content:
                        consolidated_html.append(html_content)
                        self.state.processed_files.add(input_file)
                    elif not self.error_tolerance:
                        raise ConsolidationError(f"Failed to process {input_file} after {self.retry_count} attempts")
                    
                    # Check resources after each file
                    await self.resource_manager.check_resources()

                # Generate final PDF
                if consolidated_html:
                    await self.html_processor.generate_pdf(
                        "\n".join(consolidated_html),
                        output_file
                    )

        except Exception as e:
            self.logger.error(
                "Consolidation failed",
                error=str(e),
                failed_files=len(self.state.failed_files)
            )
            raise ConsolidationError(f"Consolidation failed: {e}")
        finally:
            await self.resource_manager.cleanup()

    async def _process_file_with_retry(self, file_path: Path) -> Optional[str]:
        """
        Processes a single file with retry logic.

        Args:
            file_path: Path to the file to process

        Returns:
            HTML content if successful, None otherwise
        """
        for attempt in range(self.retry_count):
            try:
                # Convert markdown to HTML
                html_content = await self.markdown_processor.convert_to_html(file_path)
                return html_content
                
            except Exception as e:
                self.logger.error(
                    "Processing attempt failed",
                    file=str(file_path),
                    attempt=attempt + 1,
                    error=str(e)
                )
                if attempt < self.retry_count - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    self.state.failed_files[file_path] = str(e)
                    return None
