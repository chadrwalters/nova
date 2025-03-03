"""Mock implementation of the consolidate_markdown package for testing."""

from typing import Any, Dict


class Runner:
    """Mock implementation of the Runner class."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Runner instance.

        Args:
            config: Configuration dictionary.
        """
        self.config = config

    async def run(self) -> None:
        """Run the consolidation process."""
        # This is a mock implementation that does nothing
        pass
