"""Pipeline configuration and phase management.

TEMPORARY TESTING NOTE:
Currently, only the MARKDOWN_PARSE phase is enabled for testing purposes.
Other phases are temporarily disabled while we stabilize the parse phase functionality.
This is a deliberate testing strategy to ensure robust parsing before moving
to subsequent phases.
"""

import os
from pathlib import Path
from typing import Dict, Any, List

from nova.core.errors import ConfigurationError
from nova.core.logging import get_logger
from nova.core.utils import load_yaml_file

logger = get_logger(__name__)

class PipelineConfig:
    """Pipeline configuration."""

    def __init__(self, config_path: str = None):
        """Initialize pipeline configuration."""
        self.config_path = config_path
        self.config = self._load_config()
        self._filter_enabled_phases()  # TEMPORARY: Only enable MARKDOWN_PARSE

    def _load_config(self) -> Dict[str, Any]:
        """Load pipeline configuration from YAML file."""
        if not self.config_path:
            # Use default config path
            self.config_path = os.path.join(
                os.path.dirname(__file__), 
                "../../../config/pipeline_config.yaml"
            )
        
        if not os.path.exists(self.config_path):
            raise ConfigurationError(f"Pipeline config not found: {self.config_path}")
            
        return load_yaml_file(self.config_path)

    def _filter_enabled_phases(self):
        """TEMPORARY: Filter pipeline phases to only enable MARKDOWN_PARSE."""
        if "phases" not in self.config:
            return
            
        enabled_phases = {"MARKDOWN_PARSE"}
        self.config["phases"] = {
            phase: config for phase, config in self.config["phases"].items()
            if phase in enabled_phases
        }
        
        logger.info("TEMPORARY: Pipeline configured to only run MARKDOWN_PARSE phase")

    def get_phase_config(self, phase: str) -> Dict[str, Any]:
        """Get configuration for a pipeline phase."""
        if phase not in self.config.get("phases", {}):
            raise ConfigurationError(f"Phase not found in config: {phase}")
        return self.config["phases"][phase]

    def get_phases(self) -> List[str]:
        """Get list of configured pipeline phases."""
        return list(self.config.get("phases", {}).keys())

    def validate(self):
        """Validate pipeline configuration."""
        if not self.config:
            raise ConfigurationError("Empty pipeline configuration")
            
        if "phases" not in self.config:
            raise ConfigurationError("No phases defined in pipeline config")
            
        if not self.get_phases():
            raise ConfigurationError("No enabled phases in pipeline config")
            
        # Validate each phase has required fields
        required_fields = {"description", "output_dir", "processor"}
        for phase in self.get_phases():
            config = self.get_phase_config(phase)
            missing = required_fields - set(config.keys())
            if missing:
                raise ConfigurationError(
                    f"Missing required fields in {phase} config: {missing}"
                ) 