from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

class ProcessingStage(Enum):
    """Processing stages for the pipeline."""
    INDIVIDUAL = "individual"
    CONSOLIDATION = "consolidation"
    PDF_GENERATION = "pdf_generation"

class AttachmentType(Enum):
    """Types of attachments supported by the system."""
    PDF = "pdf"
    WORD = "docx"
    POWERPOINT = "pptx"
    IMAGE = "image"
    OTHER = "other"

@dataclass
class Attachment:
    """Represents a processed attachment."""
    original_path: Path
    processed_path: Path
    type: AttachmentType
    size: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    content: Optional[str] = None  # For converted content if applicable

@dataclass
class ProcessedDocument:
    """Represents a processed markdown document."""
    content: str
    source_path: Path
    processed_path: Path
    attachments: List[Attachment] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    processing_date: datetime = field(default_factory=datetime.now)

@dataclass
class ConsolidatedDocument:
    """Represents the consolidated markdown document."""
    content: str
    documents: List[ProcessedDocument]
    attachments: List[Attachment]
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_date: datetime = field(default_factory=datetime.now)

@dataclass
class ProcessingConfig:
    """Configuration for the processing pipeline."""
    input_dir: Path
    processing_dir: Path
    output_dir: Path
    template_dir: Path
    error_tolerance: str = "lenient"
    max_file_size_mb: int = 50
    max_memory_percent: int = 75
    concurrent_processes: int = 4
    
    @classmethod
    def from_env(cls) -> "ProcessingConfig":
        """Create configuration from environment variables."""
        from dotenv import load_dotenv
        import os
        
        load_dotenv()
        
        return cls(
            input_dir=Path(os.getenv("NOVA_INPUT_DIR", "")),
            processing_dir=Path(os.getenv("NOVA_PROCESSING_DIR", "")),
            output_dir=Path(os.getenv("NOVA_OUTPUT_DIR", "")),
            template_dir=Path(os.getenv("NOVA_TEMPLATE_DIR", "")),
            error_tolerance=os.getenv("NOVA_ERROR_TOLERANCE", "lenient"),
            max_file_size_mb=int(os.getenv("NOVA_MAX_FILE_SIZE_MB", "50")),
            max_memory_percent=int(os.getenv("NOVA_MAX_MEMORY_PERCENT", "75")),
            concurrent_processes=int(os.getenv("NOVA_CONCURRENT_PROCESSES", "4"))
        ) 