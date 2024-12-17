import asyncio
import tempfile
import shutil
from pathlib import Path
import structlog
import aiofiles

from src.processors.markdown_processor import MarkdownProcessor
from src.processors.attachment_processor import AttachmentProcessor
from src.generators.pdf_generator import PDFGenerator
from src.core.models import ConsolidatedDocument
from src.core.exceptions import PipelineError

logger = structlog.get_logger(__name__)

class Pipeline:
    def __init__(self, input_dir: Path, output_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.temp_dir = None

    async def run(self) -> None:
        """Run the pipeline."""
        try:
            # Create temp dir
            self.temp_dir = Path(tempfile.mkdtemp())
            media_dir = self.temp_dir / "media"
            media_dir.mkdir()

            # Initialize processors
            pdf_generator = PDFGenerator(media_dir)
            attachment_processor = AttachmentProcessor(media_dir)
            markdown_processor = MarkdownProcessor(
                temp_dir=self.temp_dir,
                media_dir=media_dir,
                error_tolerance=True
            )

            # Process files
            files = self._get_input_files()
            logger.info("Starting pipeline", file_count=len(files))

            # Process each file
            processed_docs = []
            all_attachments = []  # Track all attachments
            for file in files:
                # Read content
                async with aiofiles.open(file, 'r') as f:
                    content = await f.read()

                # Process attachments first
                content, attachments = await attachment_processor.process_attachments(
                    content,
                    file.parent,
                    self.temp_dir,
                    pdf_generator
                )
                all_attachments.extend(attachments)  # Collect attachments

                # Convert to HTML with processed content
                html = await markdown_processor.convert_to_html(file, content=content)
                processed_docs.append(html)

            # Consolidate documents
            logger.info("Consolidating documents")
            consolidated = ConsolidatedDocument(
                content="\n".join(processed_docs),
                documents=[],  # We'll add document metadata later if needed
                attachments=all_attachments,  # Add collected attachments
                metadata={}
            )

            # Generate PDF
            logger.info("Generating PDF")
            output_path = self.output_dir / "output.pdf"
            await pdf_generator.generate(consolidated, output_path)

            logger.info(
                "Pipeline completed successfully",
                output=str(output_path)
            )

        except Exception as e:
            logger.error("Pipeline failed", error=str(e))
            raise PipelineError(f"Pipeline failed: {str(e)}")

        finally:
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info("Cleanup completed")

    def _get_input_files(self) -> list[Path]:
        """Get list of markdown files to process."""
        return sorted(self.input_dir.glob("*.md"))