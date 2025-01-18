"""Tests for the nova CLI command base class."""

from typing import Any
import time

import click
import pytest
from click.testing import CliRunner
from rich.progress import Progress, TaskID

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


def test_command_success(capsys) -> None:
    """Test successful command execution."""
    runner = CliRunner()
    cmd = TestCommand()
    result = runner.invoke(cmd.create_command())
    assert result.exit_code == 0
    captured = capsys.readouterr()
    assert "SUCCESS" in captured.err


def test_command_failure(capsys) -> None:
    """Test command failure handling."""
    runner = CliRunner()
    cmd = TestCommand()
    result = runner.invoke(cmd.create_command(), ["--fail"])
    assert result.exit_code == 1
    captured = capsys.readouterr()
    assert "ERROR" in captured.err


def test_progress_creation() -> None:
    """Test progress bar creation with enhanced features."""
    cmd = TestCommand()
    progress = cmd.create_progress()

    # Verify progress columns
    column_names = [col.__class__.__name__ for col in progress.columns]
    assert "SpinnerColumn" in column_names
    assert "TextColumn" in column_names
    assert "BarColumn" in column_names
    assert "TaskProgressColumn" in column_names
    assert "MofNCompleteColumn" in column_names
    assert "TimeRemainingColumn" in column_names

    # Verify progress configuration
    assert progress.expand is True


def test_progress_stats_update() -> None:
    """Test progress statistics updates."""
    cmd = TestCommand()
    progress = cmd.create_progress()

    # Create a test task
    with progress:
        task_id = progress.add_task(
            "Test task",
            total=100,
            rate="0.0",  # Initialize rate field
            memory="0.0",  # Initialize memory field
        )

        # Update progress and verify stats
        cmd.update_progress_stats(progress, task_id, advance=10)
        task = progress.tasks[task_id]

        # Verify memory usage is tracked
        assert "memory" in task.fields
        memory = float(task.fields["memory"])
        assert memory > 0

        # Verify processing rate is tracked
        assert "rate" in task.fields
        rate = float(task.fields["rate"])
        assert rate >= 0

        # Test multiple updates
        time.sleep(0.1)  # Wait to ensure elapsed time
        cmd.update_progress_stats(progress, task_id, advance=20)
        task = progress.tasks[task_id]

        # Verify progress advances
        assert task.completed == 30

        # Verify rate calculation
        rate = float(task.fields["rate"])
        assert rate > 0  # Rate should be positive after progress
