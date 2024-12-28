"""Nova document processing system."""

from .core.utils.metrics import MetricsTracker
from .core.pipeline import PipelineManager
from .core.config import PipelineConfig

__version__ = "0.1.0"

__all__ = [
    'MetricsTracker',
    'PipelineManager',
    'PipelineConfig'
] 