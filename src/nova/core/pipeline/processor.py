"""Pipeline processor classes for Nova document processor."""

from pathlib import Path
from typing import Dict, Any, Optional, List
import os

from ..config import ProcessorConfig
from ..logging import get_logger
from ..errors import ProcessorError
from .base import BaseProcessor

logger = get_logger(__name__)

# Additional processor implementations can be added here 