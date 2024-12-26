"""Path configuration utilities."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

from ..logging import get_logger

logger = get_logger(__name__) 