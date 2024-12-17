from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

@dataclass
class ProcessedAttachment:
    """Represents a processed attachment."""
    source_path: Path
    target_path: Optional[Path]
    mime_type: str
    size: int
    metadata: dict 