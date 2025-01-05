"""Serialization utilities for Nova."""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union, cast


@dataclass
class SerializationConfig:
    """Configuration for JSON serialization."""

    indent: int = 2
    sort_keys: bool = True


def load_json(file_path: Path) -> Dict[str, Any]:
    """Load JSON data from a file.

    Args:
        file_path: Path to the JSON file

    Returns:
        Parsed JSON data as a dictionary

    Raises:
        FileNotFoundError: If the file does not exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return cast(Dict[str, Any], json.loads(f.read()))


def save_json(
    data: Dict[str, Any], file_path: Path, config: Optional[SerializationConfig] = None
) -> None:
    """Save data to a JSON file.

    Args:
        data: Data to save
        file_path: Path to save the JSON file
        config: Optional serialization configuration

    Raises:
        OSError: If the file cannot be written
        TypeError: If the data cannot be serialized to JSON
    """
    # Create parent directory if it doesn't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Use configuration if provided
    indent = config.indent if config else 2
    sort_keys = config.sort_keys if config else True

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, sort_keys=sort_keys)
