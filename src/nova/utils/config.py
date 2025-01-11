from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os

import yaml
from dotenv import load_dotenv

from nova.monitoring.config import MonitoringConfig


@dataclass
class IngestionConfig:
    chunk_size: int = 500
    heading_weight: float = 1.5


@dataclass
class EmbeddingConfig:
    model: str = "all-MiniLM-L6-v2"
    dimension: int = 384


@dataclass
class VectorStoreConfig:
    engine: str = "faiss"


@dataclass
class RAGConfig:
    top_k: int = 5


@dataclass
class LLMConfig:
    model: str = "claude-2"
    max_tokens: int = 1000
    api_key: Optional[str] = None

    def validate(self):
        """Validate LLM configuration."""
        if not self.api_key:
            self.api_key = os.getenv("CLAUDE_API_KEY")
        if not self.api_key:
            raise ValueError("CLAUDE_API_KEY must be set in environment or config")


@dataclass
class SecurityConfig:
    ephemeral_ttl: int = 300  # seconds


@dataclass
class NovaConfig:
    ingestion: IngestionConfig
    embedding: EmbeddingConfig
    vector_store: VectorStoreConfig
    rag: RAGConfig
    llm: LLMConfig
    security: SecurityConfig
    monitoring: Optional[MonitoringConfig] = None
    debug: bool = False
    log_level: str = "INFO"

    @classmethod
    def from_yaml(cls, config_path: Path) -> "NovaConfig":
        """Load configuration from YAML file."""
        load_dotenv()  # Load environment variables
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path) as f:
            config_dict = yaml.safe_load(f)
        
        monitoring_dict = config_dict.get("monitoring", {})
        monitoring_config = MonitoringConfig(**monitoring_dict) if monitoring_dict else None
        
        return cls(
            ingestion=IngestionConfig(**config_dict.get("ingestion", {})),
            embedding=EmbeddingConfig(**config_dict.get("embedding", {})),
            vector_store=VectorStoreConfig(**config_dict.get("vector_store", {})),
            rag=RAGConfig(**config_dict.get("rag", {})),
            llm=LLMConfig(**config_dict.get("llm", {})),
            security=SecurityConfig(**config_dict.get("security", {})),
            monitoring=monitoring_config,
            debug=config_dict.get("debug", False),
            log_level=config_dict.get("log_level", "INFO"),
        ) 