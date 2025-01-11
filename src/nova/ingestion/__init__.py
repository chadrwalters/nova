"""Nova ingestion module."""

from pathlib import Path
from typing import List, Optional

from nova.types import (
    Document,
    ConversionResult,
    PlaceholderResult
)


class MockDocling:
    """Mock Docling class for testing."""
    def convert(self, file_path: str) -> str:
        """Mock conversion method."""
        return f"Converted content of {file_path}"


class BearExportHandler:
    """Handles Bear.app exports."""
    
    def process_export(self, export_path: Path) -> List[Document]:
        """Process Bear.app export directory."""
        # Mock implementation for testing
        return [
            Document(
                content="Test document content",
                metadata={"source": "bear"},
                source_path=export_path / "test.md"
            )
        ]


class DoclingConverter:
    """Converts files using Docling."""
    
    def __init__(self):
        """Initialize Docling converter."""
        self.docling = MockDocling()
    
    def convert_file(self, file_path: Path) -> ConversionResult:
        """Convert single file using Docling."""
        try:
            content = self.docling.convert(str(file_path))
            return ConversionResult(
                success=True,
                content=content,
                metadata={"source": str(file_path)}
            )
        except Exception as e:
            return ConversionResult(
                success=False,
                error_message=str(e)
            )
    
    def handle_conversion_failure(self, file_path: Path) -> PlaceholderResult:
        """Generate appropriate placeholder for failed conversions."""
        return PlaceholderResult(
            original_path=file_path,
            error_message="Conversion failed",
            metadata={"source": str(file_path)}
        )
