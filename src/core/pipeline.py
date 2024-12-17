import asyncio
from pathlib import Path
from typing import List, Optional, Set
import structlog
from datetime import datetime

from src.core.models import ProcessingConfig
from src.core.exceptions import PipelineError
from src.processors.individual_processor import IndividualProcessor
from src.processors.consolidation_processor import ConsolidationProcessor
from src.processors.pdf_generator import PDFGenerator

logger = structlog.get_logger(__name__)

class Pipeline:
    """Main document processing pipeline."""

    def __init__(self, config: ProcessingConfig):
        """Initialize the pipeline.
        
        Args:
            config: Processing configuration
        """
        self.config = config
        
        # Initialize processors
        self.individual_processor = IndividualProcessor(config)
        self.consolidation_processor = ConsolidationProcessor(config)
        self.pdf_generator = PDFGenerator(config)
        
        # Create required directories
        self._create_directories()

    async def process(
        self,
        input_files: Optional[List[Path]] = None,
        output_file: Optional[Path] = None
    ) -> Path:
        """Process markdown files through the pipeline.
        
        Args:
            input_files: Optional list of specific files to process.
                        If None, processes all markdown files in input directory.
            output_file: Optional output file path.
                        If None, uses default 'output.pdf' in output directory.
            
        Returns:
            Path to generated PDF
            
        Raises:
            PipelineError: If processing fails
        """
        try:
            # Get input files
            files_to_process = input_files or self._get_input_files()
            if not files_to_process:
                raise PipelineError("No input files found")
                
            logger.info(
                "Starting pipeline",
                file_count=len(files_to_process)
            )
            
            # Process individual files
            processed_docs = []
            for file_path in files_to_process:
                try:
                    doc = await self.individual_processor.process_document(file_path)
                    processed_docs.append(doc)
                    logger.info(
                        "Processed document",
                        file=str(file_path)
                    )
                except Exception as e:
                    logger.error(
                        "Failed to process document",
                        file=str(file_path),
                        error=str(e)
                    )
                    if not self.config.error_tolerance == "lenient":
                        raise
            
            if not processed_docs:
                raise PipelineError("No documents were successfully processed")
            
            # Consolidate documents
            logger.info("Consolidating documents")
            consolidated = await self.consolidation_processor.consolidate(
                processed_docs
            )
            
            # Generate PDF
            logger.info("Generating PDF")
            output_path = await self.pdf_generator.generate(consolidated)
            
            logger.info(
                "Pipeline completed successfully",
                output=str(output_path)
            )
            
            return output_path
            
        except Exception as e:
            logger.error("Pipeline failed", error=str(e))
            raise PipelineError(
                message=f"Pipeline failed: {str(e)}",
                stage="pipeline",
                details={"error": str(e)}
            )

    def _create_directories(self) -> None:
        """Create required processing directories."""
        dirs = [
            self.config.input_dir,
            self.config.output_dir,
            self.config.processing_dir,
            self.config.processing_dir / "individual",
            self.config.processing_dir / "consolidated",
            self.config.processing_dir / "attachments",
            self.config.processing_dir / "temp"
        ]
        
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)

    def _get_input_files(self) -> List[Path]:
        """Get all markdown files from input directory.
        
        Returns:
            List of markdown file paths
        """
        return sorted(
            file for file in self.config.input_dir.rglob("*.md")
            if file.is_file()
        )

    async def cleanup(self) -> None:
        """Clean up temporary files and resources."""
        try:
            # Clean up temp directory
            temp_dir = self.config.processing_dir / "temp"
            if temp_dir.exists():
                for file in temp_dir.iterdir():
                    try:
                        if file.is_file():
                            file.unlink()
                        elif file.is_dir():
                            import shutil
                            shutil.rmtree(file)
                    except Exception as e:
                        logger.warning(
                            "Failed to clean up file",
                            file=str(file),
                            error=str(e)
                        )
                        
            logger.info("Cleanup completed")
            
        except Exception as e:
            logger.error("Cleanup failed", error=str(e)) 