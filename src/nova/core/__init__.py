"""Core pipeline initialization and configuration."""

from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console

from nova.core.utils.timing import TimingManager
from nova.core.utils.metrics import MetricsTracker
from nova.core.utils.timing_enhancements import TimingEnhancer
from nova.core.pipeline.phase_runner import PhaseRunner
from nova.core.pipeline.pipeline_reporter import PipelineReporter
from nova.core.pipeline.pipeline_manager import PipelineManager
from nova.core.config import PipelineConfig, ProcessorConfig, BaseConfig
from nova.core.logging import get_logger, setup_logging, LoggerMixin
from nova.core.errors import (
    NovaError,
    PipelineError,
    ProcessorError,
    HandlerError,
    ConfigurationError,
    StateError,
    FileError,
    ValidationError
)
from nova.core.file_operations import FileOperationsManager


__all__ = [
    'Pipeline',
    'PipelineConfig',
    'ProcessorConfig',
    'get_logger',
    'setup_logging',
    'LoggerMixin',
    'NovaError',
    'PipelineError',
    'ProcessorError',
    'ValidationError',
    'ConfigurationError',
    'FileOperationsManager',
    'PipelineManager',
    'load_config'
]


class Pipeline:
    """Main pipeline class coordinating document processing."""
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        console: Optional[Console] = None
    ):
        """Initialize pipeline with configuration.
        
        Args:
            config: Optional configuration dictionary
            console: Optional rich console instance
        """
        self.config = config or {}
        self.console = console or Console()
        
        # Initialize core components
        self.timing = TimingManager()
        self.metrics = MetricsTracker()
        self.timing_enhancer = TimingEnhancer(
            timing_manager=self.timing,
            metrics_tracker=self.metrics,
            console=self.console,
            config=self.config.get("timing", {})
        )
        
        # Set up performance thresholds
        self._configure_performance_thresholds()
        
        # Initialize pipeline components
        self.phase_runner = PhaseRunner(
            timing=self.timing,
            metrics=self.metrics,
            config=self.config
        )
        self.reporter = PipelineReporter(
            timing=self.timing,
            metrics=self.metrics,
            console=self.console
        )
        
    def _configure_performance_thresholds(self) -> None:
        """Configure performance thresholds from config."""
        timing_config = self.config.get("timing", {})
        
        # Phase throughput thresholds
        for phase, threshold in timing_config.get("phase_throughput_thresholds", {}).items():
            self.timing_enhancer.set_threshold(f"phase_{phase}_min_throughput", threshold)
            
        # Operation timing thresholds
        for op, threshold in timing_config.get("operation_timing_thresholds", {}).items():
            self.timing_enhancer.set_threshold(f"{op}_max_time", threshold)
            
        # Resource usage thresholds
        for resource, thresholds in timing_config.get("resource_thresholds", {}).items():
            for op, threshold in thresholds.items():
                self.timing_enhancer.set_threshold(f"{op}_{resource}_max", threshold)
                
    def run(self) -> None:
        """Run the pipeline phases."""
        try:
            # Start pipeline timing
            with self.timing.timer("pipeline_total"):
                # Run phases
                self.phase_runner.run_phases()
                
                # Generate performance report
                self.console.print("\nPerformance Analysis:")
                self.console.print(self.timing_enhancer.generate_timing_report())
                
                # Check for performance alerts
                alerts = self.timing_enhancer.get_alerts()
                if alerts:
                    self.console.print("\n[yellow]Performance Alerts:[/yellow]")
                    for alert in alerts:
                        self.console.print(
                            f"[yellow]- {alert.operation}: {alert.metric} = "
                            f"{alert.value:.2f} (threshold: {alert.threshold:.2f})[/yellow]"
                        )
                        
        finally:
            # Clear timing data
            self.timing_enhancer.clear()
            
    def analyze_performance(
        self,
        operation: Optional[str] = None,
        phase: Optional[str] = None
    ) -> None:
        """Analyze performance metrics for operation or phase.
        
        Args:
            operation: Optional operation name to analyze
            phase: Optional phase name to analyze
        """
        if operation:
            # Analyze operation timing
            trends = self.timing_enhancer.analyze_timing_trends(operation)
            if trends:
                self.console.print(f"\nTiming Analysis for {operation}:")
                for metric, value in trends.items():
                    if metric != "distribution":
                        self.console.print(f"- {metric}: {value}")
                        
                if "distribution" in trends:
                    self.console.print("\nTiming Distribution:")
                    for bucket, count in trends["distribution"].items():
                        self.console.print(f"- {bucket}: {count} operations")
                        
        if phase:
            # Analyze phase performance
            result = self.timing_enhancer.benchmark_phase(phase)
            if result:
                self.console.print(f"\nPhase Performance for {phase}:")
                self.console.print(f"- Throughput: {result.value:.2f} {result.unit}")
                for key, value in result.metadata.items():
                    self.console.print(f"- {key}: {value}")
                    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get all performance metrics.
        
        Returns:
            Dictionary of performance metrics
        """
        return {
            "timing_stats": self.timing.get_all_stats(),
            "metrics": self.metrics.get_all_metrics(),
            "benchmarks": [
                {
                    "type": b.type.name,
                    "name": b.name,
                    "value": b.value,
                    "unit": b.unit,
                    "metadata": b.metadata
                }
                for b in self.timing_enhancer.benchmarks
            ],
            "alerts": [
                {
                    "operation": a.operation,
                    "metric": a.metric,
                    "value": a.value,
                    "threshold": a.threshold,
                    "timestamp": a.timestamp.isoformat()
                }
                for a in self.timing_enhancer.get_alerts()
            ]
        }