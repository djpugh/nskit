"""Domain-specific exceptions for nskit client operations."""

from __future__ import annotations


class InitError(Exception):
    """Raised when recipe initialisation fails.

    Args:
        message: Description of the initialisation failure.
        details: Optional additional details about the failure.
    """

    def __init__(self, message: str, details: str | None = None) -> None:
        self.message = message
        self.details = details
        super().__init__(str(self))

    def __str__(self) -> str:
        """Format the error message with optional details."""
        if self.details:
            return f"{self.message}\nDetails: {self.details}"
        return self.message


class UpdateError(Exception):
    """Raised when a recipe update operation fails.

    Args:
        message: Description of the update failure.
        details: Optional additional details about the failure.
    """

    def __init__(self, message: str, details: str | None = None) -> None:
        self.message = message
        self.details = details
        super().__init__(str(self))

    def __str__(self) -> str:
        """Format the error message with optional details."""
        if self.details:
            return f"{self.message}\nDetails: {self.details}"
        return self.message


class ProjectNotRecipeBasedError(Exception):
    """Raised when a project does not have a recipe configuration file.

    Args:
        project_path: Path to the project directory.
    """

    def __init__(self, project_path: str) -> None:
        self.project_path = project_path
        super().__init__(str(self))

    def __str__(self) -> str:
        """Format the error message with project path and guidance."""
        return (
            f"Project at '{self.project_path}' is not recipe-based. "
            f"Expected a recipe configuration file in the project directory."
        )


class InvalidConfigError(Exception):
    """Raised when a recipe configuration file contains invalid content.

    Args:
        errors: List of validation error descriptions.
    """

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(str(self))

    def __str__(self) -> str:
        """Format the error message with a bulleted list of errors."""
        bullet_list = "\n".join(f"  - {error}" for error in self.errors)
        return f"Invalid recipe configuration:\n{bullet_list}"


class ConfigNotFoundError(Exception):
    """Raised when the recipe configuration file does not exist.

    Args:
        config_path: Expected path to the configuration file.
    """

    def __init__(self, config_path: str) -> None:
        self.config_path = config_path
        super().__init__(str(self))

    def __str__(self) -> str:
        """Format the error message with the expected config path."""
        return f"Recipe configuration file not found at '{self.config_path}'"


class FileSystemError(Exception):
    """Raised when a file system operation fails.

    Args:
        operation: Name of the operation that failed.
        path: Path of the file involved.
        reason: Description of why the operation failed.
    """

    def __init__(self, operation: str, path: str, reason: str) -> None:
        self.operation = operation
        self.path = path
        self.reason = reason
        super().__init__(str(self))

    def __str__(self) -> str:
        """Format the error message with operation, path, and reason."""
        return f"File system error during '{self.operation}' on '{self.path}': {self.reason}"


class GitStatusError(Exception):
    """Raised when the Git repository is not in a ready state.

    Args:
        reason: Description of why the repository is not ready.
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(str(self))

    def __str__(self) -> str:
        """Format the error message with the reason."""
        return f"Git repository is not ready: {self.reason}"
