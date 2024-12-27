"""Pipeline processor."""

from pathlib import Path
from typing import Dict, Any, Optional, List, Union

from ..errors import ValidationError
from ..utils.metrics import MetricsTracker
from ..utils.monitoring import MonitoringManager


class PipelineProcessor:
    """Base class for pipeline processors."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize processor.
        
        Args:
            config: Processor configuration
            
        Raises:
            ValidationError: If configuration is invalid
        """
        self.config = config
        self.metrics = MetricsTracker()
        self.monitoring = MonitoringManager()
        
        # Initialize paths
        self.input_dir = Path(config.get("input_dir", "")).resolve()
        self.output_dir = Path(config.get("output_dir", "")).resolve()
        self.temp_dir = Path(config.get("temp_dir", "")).resolve()
        
        # Initialize components
        self.components: Dict[str, Any] = {}
        self._initialize_components()
        
        # Initialize metrics
        self._initialize_metrics()
        
    def _initialize_components(self) -> None:
        """Initialize processor components."""
        components = self.config.get("components", {})
        if not isinstance(components, dict):
            raise ValidationError("Invalid components configuration")
            
        for name, config in components.items():
            if not isinstance(config, dict):
                raise ValidationError(f"Invalid component configuration: {name}")
            self.components[name] = config
            
    def _initialize_metrics(self) -> None:
        """Initialize processor metrics."""
        metrics = self.config.get("metrics", {})
        if not isinstance(metrics, dict):
            raise ValidationError("Invalid metrics configuration")
            
        counters = metrics.get("counters", [])
        if not isinstance(counters, list):
            raise ValidationError("Invalid counters configuration")
            
        for counter in counters:
            if counter not in self.metrics.counters:
                self.metrics.register_counter(counter)
                
    def validate_component(self, name: str, config: Dict[str, Any]) -> None:
        """Validate a component configuration.
        
        Args:
            name: Component name
            config: Component configuration
            
        Raises:
            ValidationError: If configuration is invalid
        """
        if name not in self.components:
            raise ValidationError(f"Unknown component: {name}")
            
        required_keys = self.components[name].get("required_keys", [])
        for key in required_keys:
            if key not in config:
                raise ValidationError(f"Missing required key for {name}: {key}")
                
    def register_metric(self, name: str) -> None:
        """Register a metric.
        
        Args:
            name: Metric name
            
        Raises:
            ValidationError: If metric is invalid
        """
        if name in self.metrics.counters:
            raise ValidationError(f"Metric already registered: {name}")
            
        self.metrics.register_counter(name)
        
    def register_monitor(self, name: str) -> None:
        """Register a monitor.
        
        Args:
            name: Monitor name
            
        Raises:
            ValidationError: If monitor is invalid
        """
        if not isinstance(name, str):
            raise ValidationError("Invalid monitor name")
            
        self.monitoring.register_phase(name)
        
    def register_error(self, name: str, message: str) -> None:
        """Register an error.
        
        Args:
            name: Error name
            message: Error message
            
        Raises:
            ValidationError: If error is invalid
        """
        if not isinstance(name, str):
            raise ValidationError("Invalid error name")
            
        self.metrics.increment_counter(f"error_{name}")
        self.monitoring.record_metric(
            name=f"error_{name}",
            value=message,
            tags={"type": "error"}
        )
        
    def register_cache(self, name: str, max_size: int) -> None:
        """Register a cache.
        
        Args:
            name: Cache name
            max_size: Maximum cache size
            
        Raises:
            ValidationError: If cache is invalid
        """
        if not isinstance(name, str):
            raise ValidationError("Invalid cache name")
            
        if not isinstance(max_size, int) or max_size <= 0:
            raise ValidationError("Invalid cache size")
            
    def process(self, input_file: Union[str, Path]) -> None:
        """Process input file.
        
        Args:
            input_file: Input file path
            
        Raises:
            ValidationError: If processing fails
        """
        input_path = Path(input_file).resolve()
        if not input_path.exists():
            raise ValidationError(f"Input file not found: {input_path}")
            
        if not input_path.is_file():
            raise ValidationError(f"Not a file: {input_path}")
            
        # Implement processing logic in derived classes
        raise NotImplementedError("Process method must be implemented by derived classes")
        
    def cleanup(self) -> None:
        """Clean up processor resources."""
        self.metrics.clear()
        self.monitoring.clear() 