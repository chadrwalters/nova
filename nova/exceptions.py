"""
Custom exception classes for the Nova CLI tool.

This module defines custom exception classes for different types of errors.
"""

from typing import Optional


class NovaError(Exception):
    """
    Base exception class for all Nova-specific errors.
    """

    def __init__(self, message: str, exit_code: int = 1):
        """
        Initialize the exception.

        Args:
            message: Error message.
            exit_code: Exit code to use when this exception causes program termination.
        """
        self.message = message
        self.exit_code = exit_code
        super().__init__(message)


class ConfigurationError(NovaError):
    """
    Exception raised for configuration-related errors.
    """

    def __init__(
        self, message: str, config_file: Optional[str] = None, exit_code: int = 2
    ):
        """
        Initialize the exception.

        Args:
            message: Error message.
            config_file: Path to the configuration file that caused the error.
            exit_code: Exit code to use when this exception causes program termination.
        """
        self.config_file = config_file
        if config_file:
            message = f"{message} (config file: {config_file})"
        super().__init__(message, exit_code)


class ConsolidationError(NovaError):
    """
    Exception raised for errors during Markdown consolidation.
    """

    def __init__(
        self, message: str, file_path: Optional[str] = None, exit_code: int = 3
    ):
        """
        Initialize the exception.

        Args:
            message: Error message.
            file_path: Path to the file that caused the error.
            exit_code: Exit code to use when this exception causes program termination.
        """
        self.file_path = file_path
        if file_path:
            message = f"{message} (file: {file_path})"
        super().__init__(message, exit_code)


class UploadError(NovaError):
    """
    Exception raised for errors during Markdown upload.
    """

    def __init__(
        self, message: str, file_path: Optional[str] = None, exit_code: int = 4
    ):
        """
        Initialize the exception.

        Args:
            message: Error message.
            file_path: Path to the file that caused the error.
            exit_code: Exit code to use when this exception causes program termination.
        """
        self.file_path = file_path
        if file_path:
            message = f"{message} (file: {file_path})"
        super().__init__(message, exit_code)


class GraphlitClientError(NovaError):
    """
    Exception raised for errors related to the Graphlit client.
    """

    def __init__(
        self, message: str, response: Optional[dict] = None, exit_code: int = 5
    ):
        """
        Initialize the exception.

        Args:
            message: Error message.
            response: Response from the Graphlit API that caused the error.
            exit_code: Exit code to use when this exception causes program termination.
        """
        self.response = response
        if response:
            message = f"{message} (response: {response})"
        super().__init__(message, exit_code)
