"""Unit tests for ContextProvider."""
from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from nskit.client.context import ContextProvider


class TestContextProvider(unittest.TestCase):
    """Tests for ContextProvider built-in context helpers."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.provider = ContextProvider()

    def test_get_context_returns_all_keys(self) -> None:
        """get_context returns a dict with all expected keys."""
        ctx = self.provider.get_context()
        expected_keys = {"username", "git_email", "git_name", "date", "year", "hostname"}
        self.assertEqual(set(ctx.keys()), expected_keys)

    def test_get_context_values_are_strings(self) -> None:
        """All context values should be strings."""
        ctx = self.provider.get_context()
        for key, value in ctx.items():
            self.assertIsInstance(value, str, f"Context key '{key}' is not a string")

    @patch("nskit.client.context.getpass.getuser", return_value="testuser")
    def test_get_username(self, _mock: unittest.mock.MagicMock) -> None:
        """_get_username returns the OS username."""
        self.assertEqual(self.provider._get_username(), "testuser")

    @patch("nskit.client.context.getpass.getuser", side_effect=OSError("no user"))
    def test_get_username_fallback(self, _mock: unittest.mock.MagicMock) -> None:
        """_get_username returns empty string on failure."""
        self.assertEqual(self.provider._get_username(), "")

    @patch("nskit.client.context.subprocess.run")
    def test_get_git_email(self, mock_run: unittest.mock.MagicMock) -> None:
        """_get_git_email returns the git user.email."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="dev@example.com\n")
        self.assertEqual(self.provider._get_git_email(), "dev@example.com")

    @patch("nskit.client.context.subprocess.run", side_effect=FileNotFoundError)
    def test_get_git_email_fallback(self, _mock: unittest.mock.MagicMock) -> None:
        """_get_git_email returns empty string when git is not installed."""
        self.assertEqual(self.provider._get_git_email(), "")

    @patch("nskit.client.context.subprocess.run")
    def test_get_git_name(self, mock_run: unittest.mock.MagicMock) -> None:
        """_get_git_name returns the git user.name."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="Test User\n")
        self.assertEqual(self.provider._get_git_name(), "Test User")

    @patch("nskit.client.context.subprocess.run", side_effect=FileNotFoundError)
    def test_get_git_name_fallback(self, _mock: unittest.mock.MagicMock) -> None:
        """_get_git_name returns empty string when git is not installed."""
        self.assertEqual(self.provider._get_git_name(), "")

    def test_get_current_date_format(self) -> None:
        """_get_current_date returns an ISO date string (YYYY-MM-DD)."""
        date_str = self.provider._get_current_date()
        self.assertRegex(date_str, r"^\d{4}-\d{2}-\d{2}$")

    def test_get_current_year_format(self) -> None:
        """_get_current_year returns a four-digit year string."""
        year_str = self.provider._get_current_year()
        self.assertRegex(year_str, r"^\d{4}$")

    @patch("nskit.client.context.socket.gethostname", return_value="myhost")
    def test_get_hostname(self, _mock: unittest.mock.MagicMock) -> None:
        """_get_hostname returns the machine hostname."""
        self.assertEqual(self.provider._get_hostname(), "myhost")

    @patch("nskit.client.context.socket.gethostname", side_effect=OSError)
    def test_get_hostname_fallback(self, _mock: unittest.mock.MagicMock) -> None:
        """_get_hostname returns empty string on failure."""
        self.assertEqual(self.provider._get_hostname(), "")


if __name__ == "__main__":
    unittest.main()
