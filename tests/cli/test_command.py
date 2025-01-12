"""Tests for the nova CLI command base class."""

from typing import Any

import click
from click.testing import CliRunner

from nova.cli.utils.command import NovaCommand


class TestCommand(NovaCommand):
    """Test command implementation."""

    name = "test"
    help = "Test command"

    def run(self, **kwargs: Any) -> None:
        """Run the test command."""
        if kwargs.get("fail"):
            self.log_error("Test failure")
            raise Exception("Test failure")
        self.log_success("Test success")

    def create_command(self) -> click.Command:
        """Create the test command with options."""

        @click.command(name=self.name, help=self.help)
        @click.option("--fail", is_flag=True, help="Trigger a failure")
        def command(**kwargs: Any) -> None:
            self.run(**kwargs)

        return command


def test_command_success() -> None:
    """Test successful command execution."""
    runner = CliRunner()
    cmd = TestCommand()
    result = runner.invoke(cmd.create_command())
    assert result.exit_code == 0
    assert "SUCCESS" in result.output


def test_command_failure() -> None:
    """Test command failure handling."""
    runner = CliRunner()
    cmd = TestCommand()
    result = runner.invoke(cmd.create_command(), ["--fail"])
    assert result.exit_code == 1
    assert "ERROR" in result.output


def test_command_help() -> None:
    """Test command help text."""
    runner = CliRunner()
    cmd = TestCommand()
    result = runner.invoke(cmd.create_command(), ["--help"])
    assert result.exit_code == 0
    assert "Test command" in result.output
