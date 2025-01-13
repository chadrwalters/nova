"""Unit tests for list tool."""

import json
from pathlib import Path

import pytest

from nova.server.tools.list import ListTool
from nova.server.types import ResourceError, ToolType


def test_initialization(tmp_path: Path) -> None:
    """Test list tool initialization."""
    # Create schema file
    schema_path = tmp_path / "list_tool.json"
    schema_path.write_text("{}")

    # Initialize tool
    tool = ListTool(schema_path)

    # Check metadata
    metadata = tool.get_metadata()
    assert metadata["id"] == "list"
    assert metadata["type"] == ToolType.LIST
    assert metadata["name"] == "List Tool"
    assert metadata["version"] == "0.1.0"
    assert "path" in metadata["parameters"]
    assert "recursive" in metadata["parameters"]
    assert "filters" in metadata["parameters"]
    assert "list" in metadata["capabilities"]


def test_list(tmp_path: Path) -> None:
    """Test list functionality."""
    # Create test directory structure
    test_dir = tmp_path / "test"
    test_dir.mkdir()
    (test_dir / "file1.txt").write_text("test1")
    (test_dir / "file2.txt").write_text("test2")
    subdir = test_dir / "subdir"
    subdir.mkdir()
    (subdir / "file3.txt").write_text("test3")

    # Create schema file
    schema_path = tmp_path / "list_tool.json"
    schema_path.write_text("{}")

    # Initialize tool
    tool = ListTool(schema_path)

    # Test basic listing
    request = {"path": str(test_dir), "recursive": False}
    result = tool.list(request)
    assert result["path"] == str(test_dir)
    assert len(result["entries"]) == 3
    assert result["metadata"]["total"] == 3
    assert not result["metadata"]["recursive"]

    # Test recursive listing
    request = {"path": str(test_dir), "recursive": True}
    result = tool.list(request)
    assert len(result["entries"]) == 4  # Including subdir contents
    assert result["metadata"]["recursive"]

    # Test type filter
    request = {"path": str(test_dir), "recursive": True, "filters": {"type": "file"}}
    result = tool.list(request)
    assert len(result["entries"]) == 3
    assert all(entry["type"] == "file" for entry in result["entries"])

    # Test name filter
    request = {"path": str(test_dir), "recursive": True, "filters": {"name": "file1"}}
    result = tool.list(request)
    assert len(result["entries"]) == 1
    assert result["entries"][0]["name"] == "file1.txt"

    # Test extension filter
    request = {
        "path": str(test_dir),
        "recursive": True,
        "filters": {"extension": ".txt"},
    }
    result = tool.list(request)
    assert len(result["entries"]) == 3
    assert all(entry["path"].endswith(".txt") for entry in result["entries"])


def test_list_validation(tmp_path: Path) -> None:
    """Test list validation."""
    # Create schema file with validation rules
    schema_path = tmp_path / "list_tool.json"
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "oneOf": [
            {
                "type": "object",
                "properties": {
                    "request": {
                        "type": "object",
                        "required": ["path"],
                        "properties": {
                            "path": {"type": "string"},
                            "recursive": {"type": "boolean"},
                            "filters": {"type": "object"},
                        },
                    }
                },
            }
        ],
    }
    schema_path.write_text(json.dumps(schema))

    # Initialize tool
    tool = ListTool(schema_path)

    # Test missing required fields
    with pytest.raises(ResourceError):
        tool.list({})

    # Test invalid path
    with pytest.raises(ResourceError, match="Path does not exist"):
        tool.list({"path": str(tmp_path / "nonexistent")})

    # Test path not a directory
    file_path = tmp_path / "test.txt"
    file_path.write_text("test")
    with pytest.raises(ResourceError, match="Path is not a directory"):
        tool.list({"path": str(file_path)})

    # Test invalid recursive type
    with pytest.raises(ResourceError):
        tool.list(
            {
                "path": str(tmp_path),
                "recursive": "true",  # Should be boolean
            }
        )

    # Test invalid filters type
    with pytest.raises(ResourceError):
        tool.list(
            {
                "path": str(tmp_path),
                "filters": "invalid",  # Should be object
            }
        )
