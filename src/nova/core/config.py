"""Configuration classes for Nova document processor."""

from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ConfigDict

from .base import PipelineConfig, ProcessorConfig, ComponentConfig 