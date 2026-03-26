"""Unit tests for GitUtils."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from nskit.client.utils.git import GitUtils


class TestGitUtilsMergeFile(unittest.TestCase):
    """Tests for GitUtils.merge_file."""

    def test_clean_merge(self) -> None:
        """Non-overlapping changes merge cleanly."""
        base = "line1\nline2\nline3\nline4\nline5\nline6\nline7\n"
        user = "line1\nuser_change\nline3\nline4\nline5\nline6\nline7\n"
        template = "line1\nline2\nline3\nline4\nline5\nline6\ntemplate_change\n"

        utils = GitUtils()
        merged, has_conflicts = utils.merge_file(base, user, template)

        self.assertFalse(has_conflicts)
        self.assertIn("user_change", merged)
        self.assertIn("template_change", merged)

    def test_conflict_merge(self) -> None:
        """Overlapping changes produce conflicts."""
        base = "line1\noriginal\nline3\n"
        user = "line1\nuser_version\nline3\n"
        template = "line1\ntemplate_version\nline3\n"

        utils = GitUtils()
        merged, has_conflicts = utils.merge_file(base, user, template)

        self.assertTrue(has_conflicts)
        # Conflict markers should be present
        self.assertIn("<<<<<<<", merged)
        self.assertIn(">>>>>>>", merged)

    def test_identical_changes_no_conflict(self) -> None:
        """Identical changes on both sides merge cleanly."""
        base = "line1\noriginal\nline3\n"
        user = "line1\nsame_change\nline3\n"
        template = "line1\nsame_change\nline3\n"

        utils = GitUtils()
        merged, has_conflicts = utils.merge_file(base, user, template)

        self.assertFalse(has_conflicts)
        self.assertIn("same_change", merged)

    def test_custom_labels(self) -> None:
        """Custom labels appear in conflict markers."""
        base = "original\n"
        user = "user\n"
        template = "template\n"

        utils = GitUtils()
        merged, has_conflicts = utils.merge_file(
            base,
            user,
            template,
            user_label="MY_USER",
            template_label="MY_TEMPLATE",
        )

        self.assertTrue(has_conflicts)
        self.assertIn("MY_USER", merged)
        self.assertIn("MY_TEMPLATE", merged)


class TestGitUtilsHasUncommittedChanges(unittest.TestCase):
    """Tests for GitUtils.has_uncommitted_changes."""

    def test_clean_repo(self) -> None:
        """A freshly committed repo has no uncommitted changes."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=tmp,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=tmp,
                capture_output=True,
            )
            (tmp_path / "file.txt").write_text("content")
            subprocess.run(["git", "add", "."], cwd=tmp, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "init"],
                cwd=tmp,
                capture_output=True,
            )

            utils = GitUtils(tmp_path)
            self.assertFalse(utils.has_uncommitted_changes())

    def test_dirty_repo(self) -> None:
        """Uncommitted changes are detected."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=tmp,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=tmp,
                capture_output=True,
            )
            (tmp_path / "file.txt").write_text("content")
            subprocess.run(["git", "add", "."], cwd=tmp, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "init"],
                cwd=tmp,
                capture_output=True,
            )
            # Create uncommitted change
            (tmp_path / "file.txt").write_text("changed")

            utils = GitUtils(tmp_path)
            self.assertTrue(utils.has_uncommitted_changes())

    def test_non_git_directory(self) -> None:
        """Non-git directory returns False."""
        with TemporaryDirectory() as tmp:
            utils = GitUtils(Path(tmp))
            self.assertFalse(utils.has_uncommitted_changes())


class TestGitUtilsIsGitRepository(unittest.TestCase):
    """Tests for GitUtils.is_git_repository."""

    def test_git_repo(self) -> None:
        """Returns True for a git repository."""
        with TemporaryDirectory() as tmp:
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            utils = GitUtils(Path(tmp))
            self.assertTrue(utils.is_git_repository())

    def test_non_git_directory(self) -> None:
        """Returns False for a non-git directory."""
        with TemporaryDirectory() as tmp:
            utils = GitUtils(Path(tmp))
            self.assertFalse(utils.is_git_repository())


class TestGitUtilsDiffFiles(unittest.TestCase):
    """Tests for GitUtils.diff_files."""

    def test_diff_identical_files(self) -> None:
        """Identical files produce empty diff."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            f1 = tmp_path / "a.txt"
            f2 = tmp_path / "b.txt"
            f1.write_text("same content")
            f2.write_text("same content")

            utils = GitUtils()
            diff = utils.diff_files(f1, f2)
            self.assertEqual(diff.strip(), "")

    def test_diff_different_files(self) -> None:
        """Different files produce non-empty diff."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            f1 = tmp_path / "a.txt"
            f2 = tmp_path / "b.txt"
            f1.write_text("old content")
            f2.write_text("new content")

            utils = GitUtils()
            diff = utils.diff_files(f1, f2)
            self.assertIn("old content", diff)
            self.assertIn("new content", diff)


if __name__ == "__main__":
    unittest.main()
