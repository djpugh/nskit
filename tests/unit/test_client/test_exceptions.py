"""Unit tests for domain exception classes."""

from __future__ import annotations

import unittest

from nskit.client.exceptions import (
    ConfigNotFoundError,
    FileSystemError,
    GitStatusError,
    InitError,
    InvalidConfigError,
    ProjectNotRecipeBasedError,
    UpdateError,
)


class TestInitError(unittest.TestCase):
    """Tests for InitError formatting."""

    def test_message_only(self) -> None:
        """String representation contains the message."""
        err = InitError("something failed")
        self.assertEqual(str(err), "something failed")

    def test_message_with_details(self) -> None:
        """String representation includes details."""
        err = InitError("failed", details="missing field")
        self.assertIn("failed", str(err))
        self.assertIn("missing field", str(err))


class TestUpdateError(unittest.TestCase):
    """Tests for UpdateError formatting."""

    def test_message_only(self) -> None:
        """String representation contains the message."""
        err = UpdateError("update broke")
        self.assertEqual(str(err), "update broke")

    def test_message_with_details(self) -> None:
        """String representation includes details."""
        err = UpdateError("broke", details="version mismatch")
        self.assertIn("broke", str(err))
        self.assertIn("version mismatch", str(err))


class TestProjectNotRecipeBasedError(unittest.TestCase):
    """Tests for ProjectNotRecipeBasedError formatting."""

    def test_includes_path(self) -> None:
        """String representation includes the project path."""
        err = ProjectNotRecipeBasedError("/tmp/myproject")
        self.assertIn("/tmp/myproject", str(err))
        self.assertIn("recipe configuration file", str(err))


class TestInvalidConfigError(unittest.TestCase):
    """Tests for InvalidConfigError formatting."""

    def test_bulleted_list(self) -> None:
        """String representation formats errors as a bulleted list."""
        err = InvalidConfigError(["bad key", "missing value"])
        msg = str(err)
        self.assertIn("- bad key", msg)
        self.assertIn("- missing value", msg)


class TestConfigNotFoundError(unittest.TestCase):
    """Tests for ConfigNotFoundError formatting."""

    def test_includes_path(self) -> None:
        """String representation includes the config path."""
        err = ConfigNotFoundError("/tmp/.recipe/config.yml")
        self.assertIn("/tmp/.recipe/config.yml", str(err))


class TestFileSystemError(unittest.TestCase):
    """Tests for FileSystemError formatting."""

    def test_includes_all_fields(self) -> None:
        """String representation includes operation, path, and reason."""
        err = FileSystemError("write", "/tmp/file.txt", "permission denied")
        msg = str(err)
        self.assertIn("write", msg)
        self.assertIn("/tmp/file.txt", msg)
        self.assertIn("permission denied", msg)


class TestGitStatusError(unittest.TestCase):
    """Tests for GitStatusError formatting."""

    def test_includes_reason(self) -> None:
        """String representation includes the reason."""
        err = GitStatusError("uncommitted changes")
        self.assertIn("uncommitted changes", str(err))


class TestBackwardCompatibility(unittest.TestCase):
    """Tests for backward compatibility of GitStatusError re-export."""

    def test_import_from_utils_git(self) -> None:
        """GitStatusError can be imported from nskit.client.utils.git."""
        from nskit.client.utils.git import GitStatusError as GitStatusErrorAlias

        self.assertIs(GitStatusErrorAlias, GitStatusError)


if __name__ == "__main__":
    unittest.main()
