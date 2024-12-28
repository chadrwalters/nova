"""Result models for handlers and processors."""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime


@dataclass
class HandlerResult:
    """Result from a handler operation."""
    
    def __init__(self, success: bool = False, content: str = "", metadata: Dict = None, errors: List[str] = None):
        """Initialize handler result.
        
        Args:
            success: Whether the operation was successful
            content: Content from the operation
            metadata: Metadata from the operation
            errors: List of error messages
        """
        self.success = success
        self.content = content
        self.metadata = metadata or {}
        self.errors = errors or []
        self.input_file = None
        self.output_dir = None
        self.output_files = []  # Initialize output_files as empty list

    success: bool = True
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def add_error(self, error: str) -> None:
        """Add an error message.
        
        Args:
            error: Error message to add
        """
        self.errors.append(error)
        self.success = False

    def add_warning(self, warning: str) -> None:
        """Add a warning message.
        
        Args:
            warning: Warning message to add
        """
        self.warnings.append(warning)

    def add_statistic(self, key: str, value: Any) -> None:
        """Add a statistic.
        
        Args:
            key: Statistic key
            value: Statistic value
        """
        self.statistics[key] = value

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value

    def set_timing(self, start_time: datetime, end_time: datetime) -> None:
        """Set timing information.
        
        Args:
            start_time: Start time
            end_time: End time
        """
        self.start_time = start_time
        self.end_time = end_time
        self.add_statistic('processing_time', (end_time - start_time).total_seconds())

    def merge(self, other: 'HandlerResult') -> None:
        """Merge another result into this one.
        
        Args:
            other: Other result to merge
        """
        self.success = self.success and other.success
        self.content = other.content or self.content
        self.metadata.update(other.metadata)
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.statistics.update(other.statistics)

        if other.start_time and (not self.start_time or other.start_time < self.start_time):
            self.start_time = other.start_time
        if other.end_time and (not self.end_time or other.end_time > self.end_time):
            self.end_time = other.end_time 


@dataclass
class ProcessingResult:
    """Result from pipeline processing."""

    success: bool = True
    phase_results: Dict[str, HandlerResult] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def add_phase_result(self, phase_name: str, result: HandlerResult) -> None:
        """Add a phase result.
        
        Args:
            phase_name: Name of the phase
            result: Result from the phase
        """
        self.phase_results[phase_name] = result
        self.success = self.success and result.success
        self.errors.extend(result.errors)
        self.warnings.extend(result.warnings)
        self.statistics.update(result.statistics)

        if result.start_time and (not self.start_time or result.start_time < self.start_time):
            self.start_time = result.start_time
        if result.end_time and (not self.end_time or result.end_time > self.end_time):
            self.end_time = result.end_time

    def add_error(self, error: str) -> None:
        """Add an error message.
        
        Args:
            error: Error message to add
        """
        self.errors.append(error)
        self.success = False

    def add_warning(self, warning: str) -> None:
        """Add a warning message.
        
        Args:
            warning: Warning message to add
        """
        self.warnings.append(warning)

    def add_statistic(self, key: str, value: Any) -> None:
        """Add a statistic.
        
        Args:
            key: Statistic key
            value: Statistic value
        """
        self.statistics[key] = value

    def set_timing(self, start_time: datetime, end_time: datetime) -> None:
        """Set timing information.
        
        Args:
            start_time: Start time
            end_time: End time
        """
        self.start_time = start_time
        self.end_time = end_time
        self.add_statistic('processing_time', (end_time - start_time).total_seconds()) 