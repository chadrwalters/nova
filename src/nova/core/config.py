"""Configuration module for Nova document processor."""

from pathlib import Path
from typing import Dict, Any, Optional, List, Set, Union
from pydantic import BaseModel, Field
import os

class OpenAIConfig(BaseModel):
    """Configuration for OpenAI integration."""
    api_key: Optional[str] = None
    model: str = "gpt-4-vision-preview"
    max_tokens: int = 500
    temperature: float = 0.7
    detail_level: str = "high"

class PathsConfig(BaseModel):
    """Configuration for paths."""
    base_dir: Path
    input_dir: Path
    output_dir: Path
    processing_dir: Path
    temp_dir: Path
    state_dir: Path
    phase_dirs: Dict[str, Path]
    image_dirs: Dict[str, Path]
    office_dirs: Dict[str, Path]

    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True

    @classmethod
    def from_nova_paths(cls, paths: 'NovaPaths') -> 'PathsConfig':
        """Create PathsConfig from NovaPaths instance."""
        return cls(
            base_dir=paths.base_dir,
            input_dir=paths.input_dir,
            output_dir=paths.output_dir,
            processing_dir=paths.processing_dir,
            temp_dir=paths.temp_dir,
            state_dir=paths.state_dir,
            phase_dirs=paths.phase_dirs,
            image_dirs=paths.image_dirs,
            office_dirs=paths.office_dirs
        )

class ProcessorConfig(BaseModel):
    """Base configuration for processors."""
    enabled: bool = True
    options: Dict[str, Any] = Field(default_factory=dict)

class MarkdownConfig(ProcessorConfig):
    """Configuration for markdown processor."""
    extensions: List[str] = [".md", ".markdown"]
    image_handling: Dict[str, bool] = {
        "copy_images": True,
        "update_paths": True
    }
    typographer: bool = True
    aggregate: Dict[str, Any] = {
        "enabled": True,
        "output_filename": "all_merged_markdown.md",
        "include_file_headers": True,
        "add_separators": True
    }

class ImageConfig(ProcessorConfig):
    """Configuration for image processor."""
    formats: List[str] = ["png", "jpg", "jpeg", "gif", "webp"]

class OfficeConfig(ProcessorConfig):
    """Configuration for office processor."""
    formats: Dict[str, List[str]] = {
        "documents": [".docx", ".doc"],
        "presentations": [".pptx", ".ppt"],
        "spreadsheets": [".xlsx", ".xls"],
        "pdf": [".pdf"]
    }

class ThreeFileSplitConfig(ProcessorConfig):
    """Configuration for three file split processor."""
    enabled: bool = True
    options: Dict[str, Any] = {
        "components": {
            "three_file_split_processor": {
                "config": {
                    "output_files": {
                        "summary": "summary.md",
                        "raw_notes": "raw_notes.md",
                        "attachments": "attachments.md"
                    },
                    "section_markers": {
                        "summary": "--==SUMMARY==--",
                        "raw_notes": "--==RAW NOTES==--",
                        "attachments": "--==ATTACHMENTS==--"
                    },
                    "cross_linking": True,
                    "preserve_headers": True
                }
            }
        }
    }

class NovaConfig(BaseModel):
    """Main configuration model."""
    paths: PathsConfig
    processors: Dict[str, ProcessorConfig] = Field(default_factory=dict)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)

    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True

    @classmethod
    def from_env(cls, paths: 'NovaPaths') -> 'NovaConfig':
        """Create NovaConfig from environment."""
        return cls(
            paths=PathsConfig.from_nova_paths(paths),
            processors={
                'markdown': MarkdownConfig(enabled=True),
                'image': ImageConfig(enabled=True),
                'office': OfficeConfig(enabled=True),
                'three_file_split': ThreeFileSplitConfig(enabled=True)
            },
            openai=OpenAIConfig(
                api_key=os.getenv('OPENAI_API_KEY'),
                model=os.getenv('OPENAI_MODEL', 'gpt-4-vision-preview'),
                max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '500')),
                temperature=float(os.getenv('OPENAI_TEMPERATURE', '0.7')),
                detail_level=os.getenv('OPENAI_DETAIL_LEVEL', 'high')
            )
        )