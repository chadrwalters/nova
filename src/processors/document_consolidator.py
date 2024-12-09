import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

import structlog

from src.core.config import ProcessingConfig
from src.core.types import ConsolidationResult, DocumentMetadata, ProcessedDocument

from .html_processor import HTMLProcessor
from .markdown_processor import MarkdownProcessor

logger = structlog.get_logger(__name__)


class DocumentConsolidator:
    """Consolidates multiple markdown documents into a single document."""

    def __init__(
        self,
        base_dir: Path,
        output_dir: Path,
        media_dir: Path,
        temp_dir: Path,
        debug_dir: Optional[Path] = None,
    ):
        self.base_dir = base_dir
        self.output_dir = output_dir
        self.media_dir = media_dir
        self.temp_dir = temp_dir
        self.debug_dir = debug_dir

        # Create debug directory structure if needed
        if self.debug_dir:
            self.debug_dir.mkdir(parents=True, exist_ok=True)

        self.config = ProcessingConfig(
            template_dir=Path("src/resources/templates"),
            media_dir=media_dir,
            relative_media_path="../_media",
            debug_dir=debug_dir,
            error_tolerance="lenient",
        )

        # Initialize processor
        self.markdown_processor = MarkdownProcessor(
            media_dir=media_dir, temp_dir=temp_dir, base_url="..", debug_dir=debug_dir
        )

        self.html_processor = HTMLProcessor(self.config)

        # Track processed files
        self.processed_files: Set[Path] = set()

        # Initialize directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.media_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def consolidate_documents(
        self, input_files: List[Path], title: str
    ) -> ConsolidationResult:
        """Consolidate multiple markdown documents into a single document."""
        try:
            # Track metadata and warnings
            all_metadata: List[DocumentMetadata] = []
            all_warnings: List[str] = []

            # Initialize output content
            output_content = [f"# {title}\n\n"]
            toc_entries: List[str] = []

            logger.info(
                "Starting consolidation",
                input_files=[str(f) for f in input_files],
                title=title,
            )

            # Process each file
            for file_path in input_files:
                try:
                    # Skip if already processed
                    if file_path in self.processed_files:
                        logger.info(
                            "Skipping already processed file", file=str(file_path)
                        )
                        continue

                    logger.info("Processing file", file=str(file_path))

                    # Read and process content
                    content = file_path.read_text(encoding="utf-8")
                    processed = self.markdown_processor.process_markdown(
                        content=content, source_path=file_path
                    )

                    # Add to processed files
                    self.processed_files.add(file_path)

                    # Add metadata
                    all_metadata.append(processed.metadata)

                    # Add warnings
                    if processed.warnings:
                        all_warnings.extend(
                            [
                                f"{file_path.name}: {warning}"
                                for warning in processed.warnings
                            ]
                        )

                    # Add to table of contents
                    if processed.metadata.title:
                        toc_entries.append(
                            f"- [{processed.metadata.title}](#{processed.metadata.title.lower().replace(' ', '-')})"
                        )

                    # Add processed content
                    output_content.append(processed.content)
                    output_content.append("\n---\n\n")

                    logger.info(
                        "Successfully processed file",
                        file=str(file_path),
                        warnings=len(processed.warnings),
                    )

                except Exception as e:
                    logger.error(
                        "File processing failed", error=str(e), file=str(file_path)
                    )
                    all_warnings.append(f"Failed to process {file_path.name}: {str(e)}")

            # Build table of contents
            toc_content = ["## Table of Contents\n\n"]
            toc_content.extend(toc_entries)
            toc_content.append("\n---\n\n")

            # Insert table of contents after title
            output_content[1:1] = toc_content

            logger.info(
                "Consolidation complete",
                processed_files=len(self.processed_files),
                warnings=len(all_warnings),
            )

            return ConsolidationResult(
                content="\n".join(output_content),
                html_files=[],  # We'll need to track these
                consolidated_html=self.output_dir / "consolidated.html",
                metadata=all_metadata,
                warnings=all_warnings,
            )

        except Exception as e:
            logger.error("Document consolidation failed", error=str(e))
            return ConsolidationResult(
                content="",
                html_files=[],
                consolidated_html=self.output_dir / "consolidated.html",
                metadata=[],
                warnings=[f"Consolidation failed: {str(e)}"],
            )

        finally:
            # Clean up
            self.cleanup()

    def cleanup(self):
        """Clean up temporary files and resources."""
        # Only cleanup temp files, preserve debug files
        if self.debug_dir != self.temp_dir / "html":
            self.markdown_processor.cleanup()

    def process_individual_files(self, input_files: List[Path]) -> List[Path]:
        """Process individual markdown files to HTML without consolidation."""
        processed_files = []

        # Process each file
        for doc_path in input_files:
            try:
                # Process markdown
                with doc_path.open() as f:
                    content = f.read()

                # Convert to HTML
                html_dir = Path(os.getenv("NOVA_DEBUG_DIR")) / "html"

                html_file = self.html_processor.convert_to_html(
                    content, doc_path, html_dir
                )
                processed_files.append(html_file)

            except Exception as e:
                logger.error(f"Failed to process {doc_path}: {str(e)}")
                if self.config.error_tolerance == "strict":
                    raise

        return processed_files


__all__ = ["DocumentConsolidator"]
