"""Context provider for built-in field default values."""

from __future__ import annotations

import getpass
import socket
import subprocess  # nosec B404
from datetime import datetime, timezone
from typing import Any


class ContextProvider:
    """Provides built-in context values for field default resolution.

    Supplies values such as the current username, git email, current date,
    etc. Each helper catches exceptions and returns an empty string on
    failure (e.g. git not installed).

    Consumers can subclass to add domain-specific context helpers.
    """

    def get_context(self) -> dict[str, Any]:
        """Return all available context values as a flat dictionary.

        Returns:
            Dictionary mapping context key names to their resolved values.
        """
        return {
            "username": self._get_username(),
            "git_email": self._get_git_email(),
            "git_name": self._get_git_name(),
            "date": self._get_current_date(),
            "year": self._get_current_year(),
            "hostname": self._get_hostname(),
        }

    def _get_username(self) -> str:
        """Return the current OS username."""
        try:
            return getpass.getuser()
        except Exception:
            return ""

    def _get_git_email(self) -> str:
        """Return the git user.email from global config."""
        return self._run_git_config("user.email")

    def _get_git_name(self) -> str:
        """Return the git user.name from global config."""
        return self._run_git_config("user.name")

    def _get_current_date(self) -> str:
        """Return today's date in ISO format (YYYY-MM-DD)."""
        try:
            return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        except Exception:
            return ""

    def _get_current_year(self) -> str:
        """Return the current four-digit year."""
        try:
            return datetime.now(tz=timezone.utc).strftime("%Y")
        except Exception:
            return ""

    def _get_hostname(self) -> str:
        """Return the machine hostname."""
        try:
            return socket.gethostname()
        except Exception:
            return ""

    def _run_git_config(self, key: str) -> str:
        """Run ``git config --global <key>`` and return the value.

        Args:
            key: Git config key to query.

        Returns:
            The config value, or an empty string on failure.
        """
        try:
            result = subprocess.run(  # nosec B603, B607
                ["git", "config", "--global", key],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except Exception:
            return ""
