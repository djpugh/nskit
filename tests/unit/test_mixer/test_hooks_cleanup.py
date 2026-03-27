"""Tests for cleanup hooks."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from nskit.mixer.hooks.cleanup import CleanupHook, RemoveEmptyDirectoriesHook, RemoveEmptyFilesHook


class TestRemoveEmptyFilesHook(unittest.TestCase):
    """Tests for RemoveEmptyFilesHook."""

    def test_removes_empty_files(self):
        """Empty files are removed."""
        with TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "empty.txt").write_text("")
            (p / "notempty.txt").write_text("content")

            hook = RemoveEmptyFilesHook()
            hook.call(p, {})

            self.assertFalse((p / "empty.txt").exists())
            self.assertTrue((p / "notempty.txt").exists())

    def test_skips_gitkeep_by_default(self):
        """Empty .gitkeep files are preserved by default."""
        with TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / ".gitkeep").write_text("")

            hook = RemoveEmptyFilesHook()
            hook.call(p, {})

            self.assertTrue((p / ".gitkeep").exists())

    def test_removes_gitkeep_when_configured(self):
        """Empty .gitkeep files are removed when skip_gitkeep=False."""
        with TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / ".gitkeep").write_text("")

            hook = RemoveEmptyFilesHook(skip_gitkeep=False)
            hook.call(p, {})

            self.assertFalse((p / ".gitkeep").exists())

    def test_nonexistent_path_returns_none(self):
        """Non-existent path returns None."""
        hook = RemoveEmptyFilesHook()
        result = hook.call(Path("/nonexistent"), {})
        self.assertIsNone(result)


class TestRemoveEmptyDirectoriesHook(unittest.TestCase):
    """Tests for RemoveEmptyDirectoriesHook."""

    def test_removes_empty_dirs(self):
        """Empty directories are removed."""
        with TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "empty_dir").mkdir()
            (p / "notempty_dir").mkdir()
            (p / "notempty_dir" / "file.txt").write_text("content")

            hook = RemoveEmptyDirectoriesHook()
            hook.call(p, {})

            self.assertFalse((p / "empty_dir").exists())
            self.assertTrue((p / "notempty_dir").exists())

    def test_nonexistent_path_returns_none(self):
        """Non-existent path returns None."""
        hook = RemoveEmptyDirectoriesHook()
        result = hook.call(Path("/nonexistent"), {})
        self.assertIsNone(result)


class TestCleanupHook(unittest.TestCase):
    """Tests for CleanupHook."""

    def test_removes_both(self):
        """Removes empty files and directories."""
        with TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "empty.txt").write_text("")
            (p / "empty_dir").mkdir()
            (p / "keep.txt").write_text("content")

            hook = CleanupHook()
            hook.call(p, {})

            self.assertFalse((p / "empty.txt").exists())
            self.assertFalse((p / "empty_dir").exists())
            self.assertTrue((p / "keep.txt").exists())

    def test_nonexistent_path_returns_none(self):
        """Non-existent path returns None."""
        hook = CleanupHook()
        result = hook.call(Path("/nonexistent"), {})
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
