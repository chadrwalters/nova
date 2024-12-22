"""Summary module for Nova document processor."""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from pathlib import Path

@dataclass
class ProcessingSummary:
    """Summary of document processing."""
    
    # File statistics
    processed_files: Dict[str, List[Path]] = field(default_factory=lambda: {
        'markdown': [],
        'pdf': [],
        'office': [],
        'image': [],
        'other': [],
        'text': []
    })
    skipped_files: Dict[str, List[Path]] = field(default_factory=lambda: {
        'unchanged': [],
        'unsupported': [],
        'error': []
    })
    
    # Image statistics
    total_images: int = 0
    processed_images: int = 0
    images_with_descriptions: int = 0
    failed_images: int = 0
    
    # API statistics
    api_calls: int = 0
    api_time_total: float = 0.0
    cache_hits: int = 0
    
    # Error tracking
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_processed(self, file_type: str, path: Path) -> None:
        """Add a successfully processed file."""
        self.processed_files[file_type].append(path)
    
    def add_skipped(self, reason: str, path: Path) -> None:
        """Add a skipped file."""
        self.skipped_files[reason].append(path)
    
    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)
    
    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary."""
        return {
            'files': {
                'processed': {k: [str(p) for p in v] for k, v in self.processed_files.items()},
                'skipped': {k: [str(p) for p in v] for k, v in self.skipped_files.items()}
            },
            'images': {
                'total': self.total_images,
                'processed': self.processed_images,
                'with_descriptions': self.images_with_descriptions,
                'failed': self.failed_images
            },
            'api': {
                'calls': self.api_calls,
                'time_total': self.api_time_total,
                'cache_hits': self.cache_hits
            },
            'errors': self.errors,
            'warnings': self.warnings
        }