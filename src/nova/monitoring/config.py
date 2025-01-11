"""Configuration for Nova monitoring system."""

from dataclasses import dataclass, field
from typing import Optional, List
import os
from pathlib import Path
import yaml


@dataclass
class AlertingConfig:
    """Configuration for alerting thresholds."""
    
    # Query performance thresholds
    max_query_latency: float = 5.0  # seconds
    max_error_rate: float = 0.05  # 5%
    
    # Resource usage thresholds
    max_memory_usage: int = 2 * 1024 * 1024 * 1024  # 2GB
    max_vector_store_size: int = 1000000  # 1M vectors
    
    # API thresholds
    min_rate_limit_remaining: int = 100
    rate_limit_warning_threshold: float = 0.2  # 20% remaining
    
    # Logging configuration
    log_path: str = "logs/alerts.log"


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
    """Configuration for monitoring system."""
    
    enabled: bool = True
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    alerting: AlertingConfig = field(default_factory=AlertingConfig)
    log_path: str = field(default_factory=lambda: "logs/nova.log")
    
    @classmethod
    def from_yaml(cls, config_path: Path) -> "MonitoringConfig":
        """Load monitoring configuration from YAML file."""
        if not config_path.exists():
            return cls()
            
        with open(config_path) as f:
            config_dict = yaml.safe_load(f)
            
        monitoring_dict = config_dict.get("monitoring", {})
        
        return cls(
            enabled=monitoring_dict.get("enabled", True),
            metrics=MetricsConfig(**monitoring_dict.get("metrics", {})),
            alerting=AlertingConfig(**monitoring_dict.get("alerting", {})),
            log_path=monitoring_dict["log_path"] if "log_path" in monitoring_dict else "logs/nova.log"
        )
        
    def validate(self) -> None:
        """Validate monitoring configuration."""
        if self.enabled:
            # Validate port is available
            if self.metrics.port < 1024:
                raise ValueError("Metrics port must be >= 1024")
                
            # Validate log path if specified
            if self.log_path:
                if not self.log_path.parent.exists():
                    raise ValueError(f"Log directory does not exist: {self.log_path.parent}")
                if not os.access(self.log_path.parent, os.W_OK):
                    raise ValueError(f"Log directory is not writable: {self.log_path.parent}")
                    
            # Validate thresholds are reasonable
            if self.alerting.max_query_latency <= 0:
                raise ValueError("max_query_latency must be positive")
            if not 0 <= self.alerting.max_error_rate <= 1:
                raise ValueError("max_error_rate must be between 0 and 1")
            if self.alerting.max_memory_usage <= 0:
                raise ValueError("max_memory_usage must be positive")
            if self.alerting.max_vector_store_size <= 0:
                raise ValueError("max_vector_store_size must be positive") 