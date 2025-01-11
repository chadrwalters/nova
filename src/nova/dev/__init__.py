"""Development utilities for Nova."""

import os
import time
import logging
import functools
from pathlib import Path
from typing import Optional, Callable, Any, Dict
from contextlib import contextmanager

import yaml
from prometheus_client import start_http_server

logger = logging.getLogger(__name__)


class DevMode:
    """Development mode configuration and utilities."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize development mode.
        
        Args:
            config_path: Path to dev config file (defaults to config/nova.dev.yaml)
        """
        self.config_path = config_path or "config/nova.dev.yaml"
        self.config = self._load_config()
        self._setup_logging()
        self._setup_directories()
        self._start_metrics()
    
    def _load_config(self) -> dict:
        """Load development configuration."""
        try:
            with open(self.config_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Failed to load dev config: {e}")
            return {}
    
    def _setup_logging(self):
        """Configure development logging."""
        if self.config.get("dev_mode", {}).get("debug_logging"):
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
    
    def _setup_directories(self):
        """Create development directories."""
        dirs = [
            self.config["core"]["temp_dir"],
            self.config["core"]["cache_dir"],
            self.config["tools"]["profiler"]["output_dir"]
        ]
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    def _start_metrics(self):
        """Start metrics server if enabled."""
        if self.config["monitoring"]["enabled"]:
            try:
                start_http_server(self.config["monitoring"]["metrics_port"])
            except Exception as e:
                logger.warning(f"Failed to start metrics server: {e}")


class MockData:
    """Mock data management for development."""
    
    def __init__(self, dev_mode: DevMode):
        """Initialize mock data manager."""
        self.config = dev_mode.config["mocks"]
        self.data_dir = Path(self.config["data_dir"])
    
    def load_scenario(self, name: str) -> Dict[str, Any]:
        """Load mock data scenario."""
        if name not in self.config["scenarios"]:
            raise ValueError(f"Unknown scenario: {name}")
        
        scenario_path = self.data_dir / f"{name}.yaml"
        try:
            with open(scenario_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load scenario {name}: {e}")
            return {}


class DevTools:
    """Development tools and utilities."""
    
    def __init__(self, dev_mode: DevMode):
        """Initialize development tools."""
        self.config = dev_mode.config["tools"]
    
    @contextmanager
    def profile(self, name: str):
        """Profile a code block."""
        if not self.config["profiler"]["enabled"]:
            yield
            return
        
        import cProfile
        import pstats
        
        profiler = cProfile.Profile()
        try:
            profiler.enable()
            yield
        finally:
            profiler.disable()
            output_dir = Path(self.config["profiler"]["output_dir"])
            stats_path = output_dir / f"{name}_{int(time.time())}.stats"
            profiler.dump_stats(str(stats_path))
            
            # Print summary
            stats = pstats.Stats(str(stats_path))
            stats.sort_stats("cumulative")
            stats.print_stats(20)
    
    def mock_response(self, data: Any) -> Callable:
        """Decorator to mock function responses."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if self.config.get("testing", {}).get("mock_responses"):
                    return data
                return func(*args, **kwargs)
            return wrapper
        return decorator


def initialize_dev_mode(config_path: Optional[str] = None) -> DevMode:
    """Initialize development mode with all utilities.
    
    Args:
        config_path: Optional path to dev config file
        
    Returns:
        Configured DevMode instance
    """
    dev_mode = DevMode(config_path)
    
    # Set environment variables
    os.environ["NOVA_ENV"] = "development"
    os.environ["NOVA_CONFIG"] = dev_mode.config_path
    
    # Initialize components
    mock_data = MockData(dev_mode)
    dev_tools = DevTools(dev_mode)
    
    return dev_mode


# Example usage:
if __name__ == "__main__":
    # Initialize dev mode
    dev_mode = initialize_dev_mode()
    
    # Use mock data
    mock_data = MockData(dev_mode)
    test_data = mock_data.load_scenario("basic_load")
    
    # Use dev tools
    tools = DevTools(dev_mode)
    
    # Profile a function
    with tools.profile("test_function"):
        time.sleep(1)  # Simulate work
    
    # Mock a response
    @tools.mock_response({"status": "success"})
    def api_call():
        return {"status": "error"} 