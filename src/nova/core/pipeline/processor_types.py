"""Processor type definitions."""

from typing import Protocol, Dict, Any, Optional, Union
from pathlib import Path


class BaseProcessor(Protocol):
    """Base protocol for all processors."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize processor."""
        ...

    def validate(self) -> None:
        """Validate processor configuration."""
        ...

    async def process(self, input_files: Union[Path, list[Path]]) -> Any:
        """Process input files."""
        ...

    def cleanup(self) -> None:
        """Clean up processor resources.""" 