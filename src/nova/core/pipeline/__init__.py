"""Pipeline module for Nova document processor."""

from pathlib import Path
from typing import Optional, Dict, Any

from .base import BaseProcessor
from .phase import PipelinePhase
from .types import PhaseType
from .manager import PipelineManager
from .processor import Pipeline

__all__ = [
    'BaseProcessor',
    'Pipeline',
    'PipelineManager',
    'PipelinePhase',
    'PhaseType'
]
