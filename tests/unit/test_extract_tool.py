"""Unit tests for extract tool."""

import json
from pathlib import Path

import pytest

from nova.server.tools.extract import ExtractTool
from nova.server.types import ResourceError, ToolType


def test_initialization(tmp_path: Path) -> None:
    """Test extract tool initialization."""
    # Create schema file
    schema_path = tmp_path / "extract_tool.json"
    schema_path.write_text("{}")

    # Initialize tool
    tool = ExtractTool(schema_path)

    # Check metadata
    metadata = tool.get_metadata()
    assert metadata["id"] == "extract"
    assert metadata["type"] == ToolType.EXTRACT
    assert metadata["name"] == "Extract Tool"
    assert metadata["version"] == "0.1.0"
    assert "source_id" in metadata["parameters"]
    assert "target_path" in metadata["parameters"]
    assert "filters" in metadata["parameters"]
    assert "extract" in metadata["capabilities"]


def test_extract(tmp_path: Path) -> None:
    """Test extract functionality."""
    # Create schema file
    schema_path = tmp_path / "extract_tool.json"
    schema_path.write_text("{}")

    # Initialize tool
    tool = ExtractTool(schema_path)

    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("This is a test file")

    # Test valid request
    request = {
        "id": "extract-1",
        "type": "extract",
        "name": "Extract Test",
        "version": "1.0.0",
        "parameters": {"source_id": "test123", "target_path": str(test_file)},
        "capabilities": ["extract"],
    }
    result = tool.extract(request)
    assert isinstance(result, dict)
    assert "id" in result
    assert "success" in result
    assert "metadata" in result
    assert result["success"] is True

    # Test missing source_id
    with pytest.raises(
        ResourceError, match="Invalid extract request: Missing source_id"
    ):
        tool.extract(
            {
                "id": "extract-2",
                "type": "extract",
                "name": "Extract Test",
                "version": "1.0.0",
                "parameters": {"target_path": "/tmp/test"},
                "capabilities": ["extract"],
            }
        )

    # Test missing target_path
    with pytest.raises(
        ResourceError, match="Invalid extract request: Missing target_path"
    ):
        tool.extract(
            {
                "id": "extract-3",
                "type": "extract",
                "name": "Extract Test",
                "version": "1.0.0",
                "parameters": {"source_id": "test123"},
                "capabilities": ["extract"],
            }
        )

    # Test invalid filters
    with pytest.raises(ResourceError, match="Invalid extract request: Invalid filters"):
        tool.extract(
            {
                "id": "extract-4",
                "type": "extract",
                "name": "Extract Test",
                "version": "1.0.0",
                "parameters": {
                    "source_id": "test123",
                    "target_path": "/tmp/test",
                    "filters": "invalid",
                },
                "capabilities": ["extract"],
            }
        )


def test_extract_validation(tmp_path: Path) -> None:
    """Test extract validation."""
    # Create schema file with validation rules
    schema_path = tmp_path / "extract_tool.json"
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "oneOf": [
            {
                "type": "object",
                "properties": {
                    "request": {
                        "type": "object",
                        "required": ["source_id", "target_path"],
                        "properties": {
                            "source_id": {"type": "string"},
                            "target_path": {"type": "string"},
                            "filters": {"type": "object"},
                        },
                    }
                },
            }
        ],
    }
    schema_path.write_text(json.dumps(schema))

    # Initialize tool
    tool = ExtractTool(schema_path)

    # Test missing required fields
    with pytest.raises(ResourceError):
        tool.extract({})

    with pytest.raises(ResourceError):
        tool.extract({"source_id": "test123"})

    with pytest.raises(ResourceError):
        tool.extract({"target_path": "/tmp/test"})

    # Test invalid types
    with pytest.raises(ResourceError):
        tool.extract(
            {
                "source_id": 123,  # Should be string
                "target_path": "/tmp/test",
            }
        )

    with pytest.raises(ResourceError):
        tool.extract(
            {
                "source_id": "test123",
                "target_path": 123,  # Should be string
            }
        )

    with pytest.raises(ResourceError):
        tool.extract(
            {
                "source_id": "test123",
                "target_path": "/tmp/test",
                "filters": "invalid",  # Should be object
            }
        )
