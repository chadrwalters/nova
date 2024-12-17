import asyncio
import shutil
from pathlib import Path
import structlog
from typing import Optional, Dict, Any, Tuple, List
import aiofiles
import magic
import hashlib
from datetime import datetime

from src.core.exceptions import ProcessingError
from src.processors.models import ProcessedAttachment

logger = structlog.get_logger(__name__)