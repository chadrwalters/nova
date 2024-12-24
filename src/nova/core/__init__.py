"""Core package for Nova document processor."""

from .config import (
    HandlerConfig,
    PathConfig,
    ProcessorConfig,
    PipelineConfig
)
from .errors import (
    NovaError,
    ConfigurationError,
    ProcessingError,
    PipelineError,
    HandlerError,
    ValidationError,
    FileError,
    StateError,
    APIError
)
from .handlers import ProcessorComponent as BaseHandler
from .handlers import MarkdownComponent as MarkdownHandler
from .handlers import DocumentComponent as ConsolidationHandler
from .pipeline import PipelineManager
from .pipeline.base import BaseProcessor
from ..phases.parse.processor import MarkdownProcessor
from ..phases.consolidate.processor import ConsolidateProcessor
from ..phases.aggregate.processor import AggregateProcessor
from ..phases.split.processor import ThreeFileSplitProcessor
from .utils import (
    setup_logging,
    LoggerMixin,
    ensure_dir,
    ensure_file,
    clean_dir,
    copy_file,
    move_file,
    get_file_size,
    get_file_mtime,
    get_file_hash,
    normalize_path,
    is_subpath,
    validate_path,
    validate_required_keys,
    validate_type,
    validate_list_type,
    validate_dict_types,
    validate_enum,
    validate_range,
    validate_string
)

__all__ = [
    'HandlerConfig',
    'PathConfig',
    'ProcessorConfig',
    'PipelineConfig',
    'NovaError',
    'ConfigurationError',
    'ProcessingError',
    'PipelineError',
    'HandlerError',
    'ValidationError',
    'FileError',
    'StateError',
    'APIError',
    'BaseHandler',
    'MarkdownHandler',
    'ConsolidationHandler',
    'PipelineManager',
    'BaseProcessor',
    'MarkdownProcessor',
    'ConsolidateProcessor',
    'AggregateProcessor',
    'ThreeFileSplitProcessor',
    'setup_logging',
    'LoggerMixin',
    'ensure_dir',
    'ensure_file',
    'clean_dir',
    'copy_file',
    'move_file',
    'get_file_size',
    'get_file_mtime',
    'get_file_hash',
    'normalize_path',
    'is_subpath',
    'validate_path',
    'validate_required_keys',
    'validate_type',
    'validate_list_type',
    'validate_dict_types',
    'validate_enum',
    'validate_range',
    'validate_string'
]