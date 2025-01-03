"""Configuration settings for Nova."""
from pathlib import Path
from typing import Dict, Optional, List

from pydantic import BaseModel


class CacheConfig(BaseModel):
    """Cache configuration."""
    
    dir: Path
    enabled: bool = True
    ttl: int = 3600  # seconds


class OpenAIConfig(BaseModel):
    """OpenAI API configuration."""
    
    api_key: Optional[str] = None
    model: str = "gpt-4o"
    max_tokens: int = 500
    vision_prompt: str = (
        "Please analyze this image and provide a detailed description. "
        "If it's a screenshot, extract any visible text. "
        "If it's a photograph, describe the scene and key elements. "
        "Focus on what makes this image relevant in a note-taking context."
    )


class APIConfig(BaseModel):
    """API configuration."""
    
    openai: Optional[OpenAIConfig] = None


class PipelineConfig(BaseModel):
    """Pipeline configuration."""
    
    phases: List[str] = ["parse", "split"]
    
    @staticmethod
    def create_initial_state() -> Dict[str, Dict]:
        """Create initial pipeline state.
        
        Returns:
            Initial state dictionary
        """
        return {
            'parse': {
                'successful_files': set(),
                'failed_files': set(),
                'skipped_files': set(),
                'unchanged_files': set(),
                'reprocessed_files': set(),
                'file_type_stats': {},
                'attachments': {}  # Track attachments by parent directory
            },
            'disassemble': {
                'successful_files': set(),
                'failed_files': set(),
                'skipped_files': set(),
                'unchanged_files': set(),
                'reprocessed_files': set(),
                'attachments': {},  # Track attachments by parent directory
                'stats': {
                    'total_processed': 0,
                    'summary_files': {
                        'created': 0,
                        'empty': 0,
                        'failed': 0
                    },
                    'raw_notes_files': {
                        'created': 0,
                        'empty': 0,
                        'failed': 0
                    },
                    'attachments': {
                        'copied': 0,
                        'failed': 0
                    }
                }
            },
            'split': {
                'successful_files': set(),
                'failed_files': set(),
                'skipped_files': set(),
                'unchanged_files': set(),
                'reprocessed_files': set(),
                'section_stats': {},
                'summary_sections': 0,
                'raw_notes_sections': 0,
                'attachments': 0
            },
            'finalize': {
                'successful_files': set(),
                'failed_files': set(),
                'skipped_files': set(),
                'unchanged_files': set(),
                'reprocessed_files': set(),
                'reference_validation': {
                    'total_references': 0,
                    'valid_references': 0,
                    'invalid_references': 0,
                    'missing_references': 0
                }
            }
        }


class DebugConfig(BaseModel):
    """Debug configuration."""
    
    enabled: bool = False
    phase_flags: Dict[str, bool] = {
        "parse": False,
        "disassemble": False,
        "split": False,
        "finalize": False
    }
    state_logging: bool = False
    extra_validation: bool = False
    performance_tracking: bool = False
    memory_tracking: bool = False
    trace_files: List[str] = []  # Files to trace in detail
    break_on_error: bool = False
    dump_state: bool = False
    dump_dir: Optional[Path] = None


class LoggingConfig(BaseModel):
    """Logging configuration."""
    
    level: str = "INFO"
    file_level: str = "DEBUG"
    console_level: str = "INFO"
    log_dir: Optional[Path] = None
    format: str = "%(asctime)s [%(levelname)s] %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    handlers: List[str] = ["console", "file"]
    phase_levels: Dict[str, str] = {}  # Per-phase log levels
    handler_levels: Dict[str, str] = {}  # Per-handler log levels
    structured: bool = True  # Enable structured logging
    include_context: bool = True  # Include phase, timing, etc.


class NovaConfig(BaseModel):
    """Nova configuration."""
    
    base_dir: Path
    input_dir: Path
    output_dir: Path
    processing_dir: Path
    cache: CacheConfig
    apis: Optional[APIConfig] = None
    pipeline: Optional[PipelineConfig] = PipelineConfig()
    logging: Optional[LoggingConfig] = LoggingConfig()
    debug: Optional[DebugConfig] = DebugConfig()
    
    class Config:
        """Pydantic model configuration."""
        
        arbitrary_types_allowed = True 