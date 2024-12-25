"""Pipeline phase enums."""

from enum import Enum, auto

class PhaseType(Enum):
    """Pipeline phase types."""
    MARKDOWN_PARSE = auto()
    MARKDOWN_CONSOLIDATE = auto()
    MARKDOWN_AGGREGATE = auto()
    MARKDOWN_SPLIT_THREEFILES = auto()  # Primary name
    MARKDOWN_SPLIT = MARKDOWN_SPLIT_THREEFILES  # Alias for backward compatibility 