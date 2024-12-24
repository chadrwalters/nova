"""Processor implementations for Nova document processor."""

from pathlib import Path
from typing import Dict, Any, Optional, List

from ..config import ProcessorConfig, PipelineConfig
from ..errors import ProcessingError
from ..utils.logging import get_logger
from .base import BaseProcessor

logger = get_logger(__name__)

# Additional processor implementations can be added here 