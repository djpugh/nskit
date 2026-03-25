"""Base command class with standardised error handling."""
from __future__ import annotations

from typing import Any

import typer
from rich.console import Console

from nskit.client.exceptions import (
    ConfigNotFoundError,
    FileSystemError,
    GitStatusError,
    InitError,
    InvalidConfigError,
    ProjectNotRecipeBasedError,
    UpdateError,
)


class BaseCommand:
    """Base class for CLI commands with standardised error handling.

    Provides a ``run()`` method that wraps ``execute()`` with exception
    handling. Subclasses override ``execute()`` to implement command
    logic and optionally ``_handle_specific_exceptions()`` for
    domain-specific error handling.

    Args:
        console: Rich console instance for output.
    """

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the command with standardised exception handling.

        Args:
            *args: Positional arguments forwarded to ``execute()``.
            **kwargs: Keyword arguments forwarded to ``execute()``.

        Returns:
            The return value of ``execute()``.
        """
        return self._handle_exceptions(self.execute, *args, **kwargs)

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Command logic — override in subclasses.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Raises:
            NotImplementedError: Always, unless overridden.
        """
        raise NotImplementedError

    def _handle_exceptions(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """Wrap a callable with standardised exception handling."""
        try:
            return func(*args, **kwargs)
        except typer.Exit as exc:
            if exc.exit_code != 0:
                raise
            raise
        except (InitError, UpdateError) as exc:
            self.console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(code=1) from exc
        except (ProjectNotRecipeBasedError, InvalidConfigError, ConfigNotFoundError) as exc:
            self.console.print(f"[red]Configuration error:[/red] {exc}")
            raise typer.Exit(code=1) from exc
        except (FileSystemError, GitStatusError) as exc:
            self.console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(code=1) from exc
        except Exception as exc:
            # Let subclasses handle domain-specific exceptions first
            try:
                self._handle_specific_exceptions(exc)
            except typer.Exit:
                raise
            except Exception:  # nosec B110
                pass
            self.console.print(f"[red]An unexpected error occurred:[/red] {exc}")
            raise typer.Exit(code=1) from exc

    def _handle_specific_exceptions(self, exception: Exception) -> None:
        """Handle domain-specific exceptions — override in subclasses.

        Args:
            exception: The exception to handle.
        """
        pass
