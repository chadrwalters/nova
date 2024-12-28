"""Test markdown handlers."""

# Standard library imports
import os
from pathlib import Path
from typing import Dict, Any, Optional, Set
from unittest.mock import Mock, patch

# Third-party imports
import pytest
from rich.console import Console

# Nova package imports
from nova.core.pipeline import PipelineState
from nova.core.utils.metrics import TimingManager, MetricsTracker, MonitoringManager
from nova.phases.parse.handlers import MarkdownHandler, ConsolidationHandler


PROCESSING_DIR = Path(os.getenv('NOVA_PROCESSING_DIR', '/tmp/nova_processing'))


class MockMonitoringManager:
    """Mock monitoring manager for testing."""
    
    def __init__(self):
        """Initialize mock monitoring manager."""
        self.metrics = {}
        self.errors = []
        
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, Any]] = None) -> None:
        """Record a metric."""
        self.metrics[name] = {'value': value, 'tags': tags or {}}
        
    def record_error(self, error: str) -> None:
        """Record an error."""
        self.errors.append(error) 