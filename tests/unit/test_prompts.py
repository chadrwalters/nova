"""Unit tests for the prompt manager."""

import json
from pathlib import Path

import pytest
from nova.server.prompts import NovaPromptManager
from nova.server.types import PromptContext, PromptError, PromptTemplate


@pytest.fixture
def template_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with test templates."""
    template_dir = tmp_path / "templates"
    template_dir.mkdir()

    # Create test template
    template = {
        "id": "test_template",
        "name": "Test Template",
        "version": "1.0.0",
        "template": "Hello ${name}! This is a ${type} template.",
        "variables": {"name": "User name", "type": "Template type"},
        "description": "A test template",
    }

    template_file = template_dir / "test_template.json"
    with open(template_file, "w") as f:
        json.dump(template, f)

    return template_dir


@pytest.fixture
def prompt_manager(template_dir: Path) -> NovaPromptManager:
    """Create a prompt manager instance."""
    return NovaPromptManager(template_dir)


def test_load_templates(prompt_manager: NovaPromptManager) -> None:
    """Test loading templates from directory."""
    template = prompt_manager.get_template("test_template")
    assert template["id"] == "test_template"
    assert template["name"] == "Test Template"
    assert template["version"] == "1.0.0"


def test_invalid_template_dir(tmp_path: Path) -> None:
    """Test error when template directory does not exist."""
    invalid_dir = tmp_path / "nonexistent"
    with pytest.raises(PromptError, match="Template directory .* does not exist"):
        NovaPromptManager(invalid_dir)


def test_get_nonexistent_template(prompt_manager: NovaPromptManager) -> None:
    """Test error when getting nonexistent template."""
    with pytest.raises(PromptError, match="Template .* not found"):
        prompt_manager.get_template("nonexistent")


def test_validate_template(prompt_manager: NovaPromptManager) -> None:
    """Test template validation."""
    valid_template = PromptTemplate(
        id="valid",
        name="Valid Template",
        version="1.0.0",
        template="Hello ${name}!",
        variables={"name": "User name"},
        description="A valid template",
    )
    assert prompt_manager.validate_template(valid_template)

    # Test missing required field
    invalid_template = PromptTemplate(
        id="invalid",
        name="Invalid Template",
        version="1.0.0",
        template="Hello ${name}!",
        variables={},  # Missing required variable
        description="An invalid template",
    )
    assert not prompt_manager.validate_template(invalid_template)


def test_assemble_context(prompt_manager: NovaPromptManager) -> None:
    """Test assembling prompt context."""
    context = PromptContext(
        template_id="test_template",
        variables={"name": "John", "type": "test"},
        system_instructions=["System instruction 1", "System instruction 2"],
        metadata={},
    )

    prompt = prompt_manager.assemble_context(context)
    assert "System instruction 1" in prompt
    assert "System instruction 2" in prompt
    assert "Hello John!" in prompt
    assert "test template" in prompt


def test_missing_variables(prompt_manager: NovaPromptManager) -> None:
    """Test error when variables are missing."""
    context = PromptContext(
        template_id="test_template",
        variables={
            "name": "John"
            # Missing 'type' variable
        },
        system_instructions=[],
        metadata={},
    )

    with pytest.raises(PromptError, match="Missing required variables"):
        prompt_manager.assemble_context(context)


def test_template_change_notification(prompt_manager: NovaPromptManager) -> None:
    """Test template change notifications."""
    notifications: dict[str, bool] = {}

    def callback(template_id: str) -> None:
        notifications[template_id] = True

    prompt_manager.on_template_change(callback)
    prompt_manager._notify_template_change("test_template")

    assert notifications["test_template"]
