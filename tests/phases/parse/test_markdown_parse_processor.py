"""Tests for the markdown parse processor."""

# Standard library imports
from pathlib import Path

# Third-party imports
import pytest
from rich.console import Console

# Nova package imports
from nova.core.config.base import ProcessorConfig, ComponentConfig
from nova.core.pipeline import PipelineState
from nova.core.utils.metrics import TimingManager, MetricsTracker, MonitoringManager
from nova.phases.parse.processor import MarkdownParseProcessor

class TestMarkdownParseProcessor:
    @pytest.fixture
    def processor(self, temp_dir, pipeline_config):
        """Create a MarkdownParseProcessor instance for testing."""
        config = ProcessorConfig(
            name="markdown_parse",
            description="Markdown processor for testing",
            input_dir=str(Path(pipeline_config.input_dir)),
            output_dir=str(Path(pipeline_config.output_dir)),
            processor="MarkdownParseProcessor",
            options={},
            components={
                "parser": ComponentConfig(
                    type="markdown",
                    config={},
                    handlers=[],
                    enabled=True
                )
            }
        )
        
        monitoring = MonitoringManager()
        timing = TimingManager()
        metrics = MetricsTracker()
        console = Console()
        pipeline_state = PipelineState(state_file=Path(temp_dir) / "pipeline_state.json")
        return MarkdownParseProcessor(
            config=config,
            monitoring=monitoring,
            timing=timing,
            metrics=metrics,
            console=console,
            pipeline_state=pipeline_state,
            pipeline_config=pipeline_config
        ) 