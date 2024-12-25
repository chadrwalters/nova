"""Core module for Nova document processor."""

from .config import (
    PipelineConfig,
    ProcessorConfig
)

from .logging import get_logger
from .errors import ProcessorError, PipelineError
from .file_ops import FileOperationsManager

__all__ = [
    'PipelineConfig',
    'ProcessorConfig',
    'get_logger',
    'ProcessorError',
    'PipelineError',
    'FileOperationsManager'
]