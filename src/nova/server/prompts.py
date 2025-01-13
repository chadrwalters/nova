"""Prompt management for the Nova MCP server."""

import json
from pathlib import Path
from string import Template
from collections.abc import Callable

from .types import PromptContext, PromptError, PromptManager, PromptTemplate


class NovaPromptManager(PromptManager):
    """Implementation of the prompt manager for Nova."""

    def __init__(self, template_dir: Path):
        """Initialize the prompt manager.

        Args:
            template_dir: Directory containing prompt templates.
        """
        self._template_dir = template_dir
        self._templates: dict[str, PromptTemplate] = {}
        self._change_callbacks: list[Callable[[str], None]] = []
        self._load_templates()

    def _load_templates(self) -> None:
        """Load templates from the template directory."""
        if not self._template_dir.exists():
            raise PromptError(f"Template directory {self._template_dir} does not exist")

        for template_file in self._template_dir.glob("*.json"):
            try:
                with open(template_file) as f:
                    template_data = json.load(f)
                    template = PromptTemplate(
                        id=template_data["id"],
                        name=template_data["name"],
                        version=template_data["version"],
                        template=template_data["template"],
                        variables=template_data["variables"],
                        description=template_data.get("description"),
                    )
                    if self.validate_template(template):
                        self._templates[template["id"]] = template
            except (json.JSONDecodeError, KeyError) as e:
                raise PromptError(f"Invalid template file {template_file}: {e}")

    def get_template(self, template_id: str) -> PromptTemplate:
        """Get prompt template by ID.

        Args:
            template_id: ID of the template to retrieve.

        Returns:
            The prompt template.

        Raises:
            PromptError: If template does not exist.
        """
        if template_id not in self._templates:
            raise PromptError(f"Template {template_id} not found")
        return self._templates[template_id]

    def validate_template(self, template: PromptTemplate) -> bool:
        """Validate prompt template.

        Args:
            template: Template to validate.

        Returns:
            True if template is valid, False otherwise.
        """
        try:
            # Check required fields
            required_fields = ["id", "name", "version", "template", "variables"]
            for field in required_fields:
                if field not in template:
                    return False

            # Validate template string
            template_str = Template(template["template"])
            test_vars = {k: "test" for k in template["variables"].keys()}
            template_str.substitute(**test_vars)

            return True
        except (KeyError, ValueError):
            return False

    def assemble_context(self, context: PromptContext) -> str:
        """Assemble prompt context into final prompt.

        Args:
            context: Context containing template ID and variables.

        Returns:
            Assembled prompt string.

        Raises:
            PromptError: If template not found or variables invalid.
        """
        template = self.get_template(context["template_id"])

        # Validate variables
        missing_vars = set(template["variables"].keys()) - set(
            context["variables"].keys()
        )
        if missing_vars:
            raise PromptError(f"Missing required variables: {missing_vars}")

        try:
            # Assemble system instructions
            system_part = "\n".join(context["system_instructions"])

            # Substitute variables in template
            template_str = Template(template["template"])
            prompt_part = template_str.substitute(**context["variables"])

            # Combine parts
            return f"{system_part}\n\n{prompt_part}"
        except (KeyError, ValueError) as e:
            raise PromptError(f"Failed to assemble prompt: {e}")

    def on_template_change(self, callback: Callable[[str], None]) -> None:
        """Register template change callback.

        Args:
            callback: Function to call when template changes.
        """
        self._change_callbacks.append(callback)

    def _notify_template_change(self, template_id: str) -> None:
        """Notify callbacks of template change.

        Args:
            template_id: ID of changed template.
        """
        for callback in self._change_callbacks:
            callback(template_id)
