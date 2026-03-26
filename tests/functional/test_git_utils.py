"""Tests for GitUtils uncovered functions."""

from pathlib import Path

import pytest

from nskit.client.utils.git import GitUtils


class TestGitUtilsAdditional:
    """Test uncovered GitUtils functions."""

    def test_get_current_commit(self, tmp_path):
        """Test getting current commit hash."""
        import subprocess

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)

        # Create and commit a file
        (tmp_path / "test.txt").write_text("test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=tmp_path, capture_output=True)

        git_utils = GitUtils(tmp_path)
        commit = git_utils.get_current_commit()

        assert commit is not None
        assert len(commit) == 40  # SHA-1 hash

    def test_has_uncommitted_changes_clean(self, tmp_path):
        """Test checking for uncommitted changes in clean repo."""
        import subprocess

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)

        # Create and commit a file
        (tmp_path / "test.txt").write_text("test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=tmp_path, capture_output=True)

        git_utils = GitUtils(tmp_path)
        has_changes = git_utils.has_uncommitted_changes()

        assert not has_changes

    def test_has_uncommitted_changes_dirty(self, tmp_path):
        """Test checking for uncommitted changes in dirty repo."""
        import subprocess

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)

        # Create and commit a file
        (tmp_path / "test.txt").write_text("test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=tmp_path, capture_output=True)

        # Modify file
        (tmp_path / "test.txt").write_text("modified")

        git_utils = GitUtils(tmp_path)
        has_changes = git_utils.has_uncommitted_changes()

        assert has_changes
