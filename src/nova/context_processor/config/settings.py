"""Configuration settings for Nova."""
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CacheConfig(BaseModel):
    """Cache configuration."""

    dir: Path
    enabled: bool = True
    ttl: int = 3600  # seconds

    model_config = ConfigDict(arbitrary_types_allowed=True)


class OpenAIConfig(BaseModel):
    """OpenAI API configuration."""

    api_key: Optional[str] = None
    base_url: Optional[str] = None  # Optional custom API endpoint
    model: str = "gpt-4o"
    max_tokens: int = 500
    vision_prompt: str = (
        "Please analyze this image and provide a detailed description. "
        "If it's a screenshot, extract any visible text. "
        "If it's a photograph, describe the scene and key elements. "
        "Focus on what makes this image relevant in a note-taking context."
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def has_valid_key(self) -> bool:
        """Check if the API key is valid."""
        if not self.api_key:
            return False
        key = self.api_key.strip()
        if not key:
            return False
        # Remove quotes if present
        if key.startswith('"') and key.endswith('"'):
            key = key[1:-1]
        # Check if key starts with expected prefix
        return key.startswith("sk-") or key.startswith("ysk-proj-")

    def get_key(self) -> Optional[str]:
        """Get the API key, properly formatted."""
        if not self.has_valid_key:
            return None
        key = self.api_key.strip()
        if key.startswith('"') and key.endswith('"'):
            key = key[1:-1]
        return key


class APIConfig(BaseModel):
    """API configuration."""

    openai: Optional[OpenAIConfig] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class PipelineConfig(BaseModel):
    """Pipeline configuration."""

    phases: List[str] = ["parse", "disassemble", "split", "finalize"]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @staticmethod
    def create_initial_state() -> Dict[str, Dict]:
        """Create initial pipeline state."""
        return {
            "parse": {
                "successful_files": set(),
                "failed_files": set(),
                "skipped_files": set(),
                "unchanged_files": set(),
                "reprocessed_files": set(),
                "file_stats": {},
                "total_files": 0,
                "processed_files": 0,
                "failed_files_count": 0,
                "skipped_files_count": 0,
                "file_type_stats": {},
                "attachments": {},
                "_file_errors": {},
            },
            "disassemble": {
                "successful_files": set(),
                "failed_files": set(),
                "skipped_files": set(),
                "unchanged_files": set(),
                "reprocessed_files": set(),
                "stats": {
                    "summary_files": {"created": 0, "empty": 0, "failed": 0},
                    "raw_notes_files": {"created": 0, "empty": 0, "failed": 0},
                    "attachments": {"copied": 0, "failed": 0},
                    "total_sections": 0,
                    "total_processed": 0,
                    "total_attachments": 0,
                    "total_outputs": 0,
                },
                "attachments": {},
                "_file_errors": {},
                "file_type_stats": {},
            },
            "split": {
                "successful_files": set(),
                "failed_files": set(),
                "skipped_files": set(),
                "unchanged_files": set(),
                "reprocessed_files": set(),
                "section_stats": {},
                "summary_sections": 0,
                "raw_notes_sections": 0,
                "attachments": set(),
                "file_type_stats": {},
                "_file_errors": {},
            },
            "finalize": {
                "successful_files": set(),
                "failed_files": set(),
                "skipped_files": set(),
                "unchanged_files": set(),
                "reprocessed_files": set(),
                "reference_validation": {
                    "total_references": 0,
                    "valid_references": 0,
                    "invalid_references": 0,
                    "missing_references": 0,
                },
                "file_type_stats": {},
                "_file_errors": {},
            },
        }


class DebugConfig(BaseModel):
    """Debug configuration."""

    enabled: bool = False
    phase_flags: Dict[str, bool] = {
        "parse": False,
        "disassemble": False,
        "split": False,
        "finalize": False,
    }
    state_logging: bool = False
    extra_validation: bool = False
    performance_tracking: bool = False
    memory_tracking: bool = False
    trace_files: List[str] = []  # Files to trace in detail
    break_on_error: bool = False
    dump_state: bool = False
    dump_dir: Optional[Path] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


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

    model_config = ConfigDict(arbitrary_types_allowed=True)


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
    input_patterns: List[str] = ["*"]  # Default to all files

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("input_dir", "output_dir", "processing_dir")
    @classmethod
    def validate_path(cls, v: Union[str, Path]) -> Path:
        """Validate path fields.

        Args:
            v: Path value to validate

        Returns:
            Validated Path object
        """
        if isinstance(v, str):
            v = Path(v)
        return v
