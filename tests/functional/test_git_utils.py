"""Tests for GitUtils uncovered functions."""

import unittest

import pytest

from nskit.client.utils.git import GitUtils


@pytest.mark.usefixtures("git_repo")
class TestGitUtilsAdditional(unittest.TestCase):
    """Test uncovered GitUtils functions."""

    def test_get_current_commit(self):
        """Test getting current commit hash."""
        git_utils = GitUtils(self.git_repo)
        commit = git_utils.get_current_commit()

        self.assertIsNotNone(commit)
        self.assertEqual(len(commit), 40)  # SHA-1 hash

    def test_has_uncommitted_changes_clean(self):
        """Test checking for uncommitted changes in clean repo."""
        git_utils = GitUtils(self.git_repo)
        has_changes = git_utils.has_uncommitted_changes()

        self.assertFalse(has_changes)

    def test_has_uncommitted_changes_dirty(self):
        """Test checking for uncommitted changes in dirty repo."""
        # Modify existing file
        (self.git_repo / "README.md").write_text("modified")

        git_utils = GitUtils(self.git_repo)
        has_changes = git_utils.has_uncommitted_changes()

        self.assertTrue(has_changes)


if __name__ == "__main__":
    unittest.main()
