"""Unit tests for remove tool."""

import json
from pathlib import Path

import pytest

from nova.server.tools.remove import RemoveTool
from nova.server.types import ResourceError, ToolType


def test_initialization(tmp_path: Path) -> None:
    """Test remove tool initialization."""
    # Create schema file
    schema_path = tmp_path / "remove_tool.json"
    schema_path.write_text("{}")

    # Initialize tool
    tool = RemoveTool(schema_path)

    # Check metadata
    metadata = tool.get_metadata()
    assert metadata["id"] == "remove"
    assert metadata["type"] == ToolType.REMOVE
    assert metadata["name"] == "Remove Tool"
    assert metadata["version"] == "0.1.0"
    assert "target_id" in metadata["parameters"]
    assert "force" in metadata["parameters"]
    assert "remove" in metadata["capabilities"]


def test_remove(tmp_path: Path) -> None:
    """Test remove functionality."""
    # Create schema file
    schema_path = tmp_path / "remove_tool.json"
    schema_path.write_text("{}")

    # Initialize tool
    tool = RemoveTool(schema_path)

    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("This is a test file")

    # Test valid request
    request = {
        "id": "remove-1",
        "type": "remove",
        "name": "Remove Test",
        "version": "1.0.0",
        "parameters": {"target_id": "test123", "force": True},
        "capabilities": ["remove"],
    }
    result = tool.remove(request)
    assert isinstance(result, dict)
    assert "id" in result
    assert "success" in result
    assert "metadata" in result
    assert result["success"] is True

    # Test missing target_id
    with pytest.raises(
        ResourceError, match="Invalid remove request: Missing target_id"
    ):
        tool.remove(
            {
                "id": "remove-2",
                "type": "remove",
                "name": "Remove Test",
                "version": "1.0.0",
                "parameters": {"force": True},
                "capabilities": ["remove"],
            }
        )

    # Test invalid force flag
    with pytest.raises(
        ResourceError, match="Invalid remove request: Invalid force flag"
    ):
        tool.remove(
            {
                "id": "remove-3",
                "type": "remove",
                "name": "Remove Test",
                "version": "1.0.0",
                "parameters": {"target_id": "test123", "force": "invalid"},
                "capabilities": ["remove"],
            }
        )


def test_remove_validation(tmp_path: Path) -> None:
    """Test remove validation."""
    # Create schema file with validation rules
    schema_path = tmp_path / "remove_tool.json"
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "oneOf": [
            {
                "type": "object",
                "properties": {
                    "request": {
                        "type": "object",
                        "required": ["target_id"],
                        "properties": {
                            "target_id": {"type": "string"},
                            "force": {"type": "boolean"},
                        },
                    }
                },
            }
        ],
    }
    schema_path.write_text(json.dumps(schema))

    # Initialize tool
    tool = RemoveTool(schema_path)

    # Test missing required fields
    with pytest.raises(ResourceError):
        tool.remove({})

    # Test invalid target_id type
    with pytest.raises(ResourceError):
        tool.remove(
            {
                "target_id": 123  # Should be string
            }
        )

    # Test invalid force type
    with pytest.raises(ResourceError):
        tool.remove(
            {
                "target_id": "test123",
                "force": "true",  # Should be boolean
            }
        )
