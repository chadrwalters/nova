import asyncio
from pathlib import Path
import structlog
import aiofiles
from typing import Optional
import weasyprint
import os

from src.core.models import ConsolidatedDocument

logger = structlog.get_logger(__name__)

class PDFGenerator:
    """Generates PDF files from consolidated documents."""
    
    def __init__(self, base_path: Path):
        """Initialize PDF generator.
        
        Args:
            base_path: Base path for resolving relative paths
        """
        self.base_path = base_path
        self.logger = logger

    async def generate(self, document: ConsolidatedDocument, output_path: Path) -> None:
        """Generate PDF from consolidated document."""
        try:
            # Verify resources exist
            await self._verify_resources()

            # Create HTML with proper resource handling
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <base href="file://{self.base_path.absolute()}/"/>
                <style>
                    @page {{
                        margin: 2cm;
                        size: A4;
                    }}
                    body {{
                        font-family: system-ui, -apple-system, sans-serif;
                        line-height: 1.5;
                        margin: 0;
                        padding: 2cm;
                    }}
                    img {{
                        max-width: 100%;
                        height: auto;
                        display: block;
                        margin: 1em auto;
                        page-break-inside: avoid;
                    }}
                    .markdown-document {{
                        margin-bottom: 2em;
                        page-break-after: always;
                    }}
                    .document-title {{
                        font-size: 24px;
                        font-weight: bold;
                        margin-bottom: 1em;
                        page-break-after: avoid;
                    }}
                    .attachment {{
                        margin: 1em 0;
                        padding: 1em;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                    }}
                    .attachment.preview {{
                        background: #f5f5f5;
                    }}
                    .attachment.embed {{
                        page-break-inside: avoid;
                    }}
                </style>
            </head>
            <body>
                {document.content}
            </body>
            </html>
            """
            
            self.logger.info(
                "Raw content for PDF generation",
                content_length=len(html_content),
                content_preview=html_content[:500]
            )

            # Generate PDF with proper base URL
            html = weasyprint.HTML(
                string=html_content,
                base_url=f"file://{self.base_path.absolute()}"
            )
            html.write_pdf(output_path)

            self.logger.info(
                "Successfully wrote PDF",
                output_path=str(output_path),
                size=output_path.stat().st_size
            )

        except Exception as e:
            self.logger.error(
                "Failed to generate PDF",
                error=str(e)
            )
            raise

    async def _verify_resources(self) -> None:
        """Verify all resources exist."""
        for resource_type in ['images', 'documents']:
            resource_dir = self.base_path / 'media' / resource_type
            if not resource_dir.exists():
                resource_dir.mkdir(parents=True)
            
            # Check all files in directory are readable
            for file_path in resource_dir.glob('*'):
                if not os.access(file_path, os.R_OK):
                    raise PermissionError(f"Cannot read resource: {file_path}")
                
                self.logger.debug(
                    "Verified resource",
                    path=str(file_path),
                    size=file_path.stat().st_size
                )