"""Tests for cleanup hooks."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from nskit.mixer.hooks.cleanup import CleanupHook, RemoveEmptyDirectoriesHook, RemoveEmptyFilesHook


class TestRemoveEmptyFilesHook(unittest.TestCase):
    """Tests for RemoveEmptyFilesHook."""

    def test_removes_empty_files(self) -> None:
        """Empty files are removed."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "empty.txt").write_text("")
            (root / "content.txt").write_text("hello")

            hook = RemoveEmptyFilesHook()
            hook.call(root, {})

            self.assertFalse((root / "empty.txt").exists())
            self.assertTrue((root / "content.txt").exists())

    def test_skips_gitkeep_by_default(self) -> None:
        """Empty .gitkeep files are preserved by default."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitkeep").write_text("")

            hook = RemoveEmptyFilesHook()
            hook.call(root, {})

            self.assertTrue((root / ".gitkeep").exists())

    def test_removes_gitkeep_when_configured(self) -> None:
        """Empty .gitkeep files are removed when skip_gitkeep is False."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitkeep").write_text("")

            hook = RemoveEmptyFilesHook(skip_gitkeep=False)
            hook.call(root, {})

            self.assertFalse((root / ".gitkeep").exists())

    def test_nonexistent_path_returns_none(self) -> None:
        """Returns None for nonexistent path."""
        hook = RemoveEmptyFilesHook()
        result = hook.call(Path("/nonexistent"), {})
        self.assertIsNone(result)

    def test_returns_path_and_context(self) -> None:
        """Returns (recipe_path, context) tuple."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx = {"key": "value"}
            result = hook = RemoveEmptyFilesHook()
            result = hook.call(root, ctx)
            self.assertEqual(result, (root, ctx))


class TestRemoveEmptyDirectoriesHook(unittest.TestCase):
    """Tests for RemoveEmptyDirectoriesHook."""

    def test_removes_empty_directories(self) -> None:
        """Empty directories are removed."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "empty_dir").mkdir()
            (root / "full_dir").mkdir()
            (root / "full_dir" / "file.txt").write_text("content")

            hook = RemoveEmptyDirectoriesHook()
            hook.call(root, {})

            self.assertFalse((root / "empty_dir").exists())
            self.assertTrue((root / "full_dir").exists())

    def test_removes_nested_empty_directories(self) -> None:
        """Nested empty directories are removed bottom-up."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a" / "b" / "c").mkdir(parents=True)

            hook = RemoveEmptyDirectoriesHook()
            hook.call(root, {})

            self.assertFalse((root / "a").exists())

    def test_nonexistent_path_returns_none(self) -> None:
        """Returns None for nonexistent path."""
        hook = RemoveEmptyDirectoriesHook()
        result = hook.call(Path("/nonexistent"), {})
        self.assertIsNone(result)


class TestCleanupHook(unittest.TestCase):
    """Tests for combined CleanupHook."""

    def test_removes_empty_files_and_dirs(self) -> None:
        """Removes both empty files and empty directories."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "empty.txt").write_text("")
            (root / "empty_dir").mkdir()
            (root / "keep.txt").write_text("content")

            hook = CleanupHook()
            hook.call(root, {})

            self.assertFalse((root / "empty.txt").exists())
            self.assertFalse((root / "empty_dir").exists())
            self.assertTrue((root / "keep.txt").exists())

    def test_files_only(self) -> None:
        """Only removes files when remove_empty_dirs is False."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "empty.txt").write_text("")
            (root / "empty_dir").mkdir()

            hook = CleanupHook(remove_empty_dirs=False)
            hook.call(root, {})

            self.assertFalse((root / "empty.txt").exists())
            self.assertTrue((root / "empty_dir").exists())

    def test_dirs_only(self) -> None:
        """Only removes dirs when remove_empty_files is False."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "empty.txt").write_text("")
            (root / "empty_dir").mkdir()

            hook = CleanupHook(remove_empty_files=False)
            hook.call(root, {})

            self.assertTrue((root / "empty.txt").exists())
            self.assertFalse((root / "empty_dir").exists())

    def test_nonexistent_path_returns_none(self) -> None:
        """Returns None for nonexistent path."""
        hook = CleanupHook()
        result = hook.call(Path("/nonexistent"), {})
        self.assertIsNone(result)

    def test_skip_gitkeep_false_propagation(self) -> None:
        """CleanupHook(skip_gitkeep=False) removes .gitkeep files."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitkeep").write_text("")

            hook = CleanupHook(skip_gitkeep=False)
            hook.call(root, {})

            self.assertFalse((root / ".gitkeep").exists())
