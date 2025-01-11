"""Nova configuration module."""

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, List
import os

import yaml
from dotenv import load_dotenv


@dataclass
class CacheConfig:
    """Cache configuration."""
    dir: str = "_Nova/cache"
    enabled: bool = True
    ttl: int = 3600


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    file: str = "_Nova/logs/nova.log"


@dataclass
class PipelineConfig:
    """Pipeline configuration."""
    phases: List[str] = field(default_factory=lambda: [
        "ingestion",
        "embedding",
        "vector_store",
        "rag",
        "llm"
    ])


def load_config(config_path: Path) -> "NovaConfig":
    """Load configuration from a YAML file."""
    return NovaConfig.from_yaml(config_path)


def validate_config(config: "NovaConfig") -> None:
    """Validate Nova configuration."""
    # Validate required paths
    for path_name, path_str in {
        "base_dir": config.base_dir,
        "input_dir": config.input_dir,
        "output_dir": config.output_dir,
        "processing_dir": config.processing_dir,
    }.items():
        path = Path(path_str)
        if not path.exists():
            path.mkdir(parents=True)

    # Validate cache
    if config.cache.enabled:
        cache_path = Path(config.cache.dir)
        if not cache_path.exists():
            cache_path.mkdir(parents=True)

    # Validate logging
    log_path = Path(config.logging.file).parent
    if not log_path.exists():
        log_path.mkdir(parents=True)


@dataclass
class APIConfig:
    openai_api_key: Optional[str] = None
    vision_prompt: Optional[str] = None


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
    provider: str = "openai"
    model: str = "gpt-3.5-turbo-16k"
    max_tokens: int = 1000
    temperature: float = 0.7
    api_key: Optional[str] = None

    def __post_init__(self):
        if not self.api_key:
            if self.provider == "openai":
                self.api_key = os.getenv("OPENAI_API_KEY")
            elif self.provider == "claude":
                self.api_key = os.getenv("ANTHROPIC_API_KEY")


@dataclass
class SecurityConfig:
    """Security configuration."""
    tls_cert_path: str = "certs/server.crt"
    tls_key_path: str = "certs/server.key"
    auth_token: str = "test-token"
    enable_tls: bool = True


@dataclass
class EmailConfig:
    """Email configuration for alerts."""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    from_addr: str = ""
    to_addrs: List[str] = field(default_factory=list)


@dataclass
class AlertingConfig:
    """Alert configuration and management."""
    
    max_query_latency: float = 1.0  # Maximum acceptable query latency in seconds
    max_error_rate: float = 0.01  # Maximum acceptable error rate (1%)
    max_memory_usage: int = 4 * 1024 * 1024 * 1024  # Maximum memory usage (4GB)
    max_vector_store_size: int = 1000000  # Maximum number of vectors in store
    min_rate_limit_remaining: int = 100  # Minimum remaining API calls before warning
    rate_limit_warning_threshold: float = 0.2  # Warn when remaining is below 20% of min
    log_path: str = "logs/alerts.log"  # Path to alert log file
    email_config: Optional[EmailConfig] = None  # Email configuration for notifications
    slack_webhook: Optional[str] = None  # Slack webhook URL for notifications

    @classmethod
    def from_dict(cls, config: dict) -> "AlertingConfig":
        """Create AlertingConfig from dictionary."""
        return cls(**config)


@dataclass
class MetricsConfig:
    """Configuration for metrics collection."""
    
    # Server configuration
    port: int = 8000
    host: str = "localhost"
    
    # Collection intervals
    memory_update_interval: int = 60  # seconds
    vector_store_update_interval: int = 300  # seconds
    
    # Histogram buckets
    latency_buckets: List[float] = field(
        default_factory=lambda: [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
    )
    memory_buckets: List[float] = field(
        default_factory=lambda: [
            100 * 1024 * 1024,  # 100MB
            500 * 1024 * 1024,  # 500MB
            1 * 1024 * 1024 * 1024,  # 1GB
            2 * 1024 * 1024 * 1024,  # 2GB
        ]
    )


@dataclass
class MonitoringConfig:
    """Configuration for monitoring."""
    enabled: bool = True
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    alerting: AlertingConfig = field(default_factory=AlertingConfig)
    log_path: str = "logs/nova.log"

    @classmethod
    def from_dict(cls, config_dict: dict) -> "MonitoringConfig":
        """Create MonitoringConfig from dictionary."""
        metrics = config_dict.get("metrics", {})
        alerting = config_dict.get("alerting", {})
        return cls(
            enabled=config_dict.get("enabled", True),
            metrics=MetricsConfig(**metrics),
            alerting=AlertingConfig(**alerting),
            log_path=config_dict.get("log_path", "logs/nova.log")
        )


@dataclass
class HandlerConfig:
    """Handler configuration."""
    image_formats: List[str] = field(default_factory=lambda: ["png", "jpg", "jpeg", "gif"])


@dataclass
class CloudConfig:
    """Cloud deployment configuration."""
    provider: str = "aws"
    region: str = "us-west-2"
    instance_type: str = "t3.medium"


@dataclass
class NovaConfig:
    """Nova configuration."""
    base_dir: Path = field(default_factory=lambda: Path("data"))
    cache_dir: Path = field(default_factory=lambda: Path("cache"))
    api: APIConfig = field(default_factory=APIConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    cloud: CloudConfig = field(default_factory=CloudConfig)
    handlers: HandlerConfig = field(default_factory=HandlerConfig)

    @classmethod
    def from_yaml(cls, config_path: str | Path) -> "NovaConfig":
        """Load configuration from YAML file."""
        load_dotenv()  # Load environment variables

        # Convert string path to Path object
        if isinstance(config_path, str):
            config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path) as f:
            config_dict = yaml.safe_load(f)

        # Update environment variables
        for key, value in config_dict.items():
            if isinstance(value, dict):
                for k, v in value.items():
                    if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                        env_var = v[2:-1]
                        config_dict[key][k] = os.getenv(env_var, "")

        # Convert cache to cache_dir if present
        if "cache" in config_dict:
            config_dict["cache_dir"] = config_dict.pop("cache")

        # Convert nested dicts to config objects
        if "api" in config_dict:
            config_dict["api"] = APIConfig(**config_dict["api"])
        if "security" in config_dict:
            config_dict["security"] = SecurityConfig(**config_dict["security"])
        if "monitoring" in config_dict:
            metrics = config_dict["monitoring"].get("metrics", {})
            alerting = config_dict["monitoring"].get("alerting", {})
            config_dict["monitoring"] = MonitoringConfig(
                enabled=config_dict["monitoring"].get("enabled", True),
                metrics=MetricsConfig(**metrics),
                alerting=AlertingConfig(**alerting)
            )
        if "cloud" in config_dict:
            config_dict["cloud"] = CloudConfig(**config_dict["cloud"])
        if "handlers" in config_dict:
            config_dict["handlers"] = HandlerConfig(**config_dict["handlers"])

        return cls(**config_dict) 