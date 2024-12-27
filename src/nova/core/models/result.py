"""Result model for processing operations."""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime

@dataclass
class ProcessingResult:
    """Result of a processing operation."""
    
    success: bool = False
    content: str = ""
    processed_files: List[Path] = field(default_factory=list)
    processed_attachments: List[Path] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    file_map: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = field(default_factory=datetime.now)
    processing_time: float = 0.0
    attachments: List[Path] = field(default_factory=list)

    def add_error(self, error: str) -> None:
        """Add an error message to the result."""
        self.errors.append(error)
        self.success = False

    def add_warning(self, warning: str) -> None:
        """Add a warning message to the result."""
        self.warnings.append(warning)

    def add_processed_file(self, file_path: Path) -> None:
        """Add a processed file to the result."""
        self.processed_files.append(file_path)

    def add_processed_attachment(self, file_path: Path) -> None:
        """Add a processed attachment to the result."""
        self.processed_attachments.append(file_path)

    def add_file_mapping(self, source: str, target: str) -> None:
        """Add a file mapping to the result."""
        self.file_map[source] = target

    def set_processing_time(self) -> None:
        """Set the processing time based on start and end times."""
        self.end_time = datetime.now()
        self.processing_time = (self.end_time - self.start_time).total_seconds()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the result to a dictionary.
        
        Returns:
            Dictionary representation of the result
        """
        return {
            "success": self.success,
            "content": self.content,
            "processed_files": [str(p) for p in self.processed_files],
            "processed_attachments": [str(p) for p in self.processed_attachments],
            "errors": self.errors,
            "warnings": self.warnings,
            "file_map": self.file_map,
            "metadata": self.metadata,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "processing_time": self.processing_time,
            "attachments": [str(p) for p in self.attachments]
        } 