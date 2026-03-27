"""Unit tests for DiffEngine."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from nskit.client.diff.engine import DiffEngine
from nskit.common.models.diff import DiffMode, DiffType


class TestDiffEngineExtractDiff(unittest.TestCase):
    """Tests for DiffEngine.extract_diff."""

    def setUp(self) -> None:
        """Create temporary directories for old and new versions."""
        self._tmp = TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.old_dir = self.tmp / "old"
        self.new_dir = self.tmp / "new"
        self.old_dir.mkdir()
        self.new_dir.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, base: Path, rel: str, content: str) -> None:
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_added_files(self) -> None:
        """Files only in new_path are reported as added."""
        self._write(self.old_dir, "keep.txt", "same")
        self._write(self.new_dir, "keep.txt", "same")
        self._write(self.new_dir, "added.txt", "new content")

        engine = DiffEngine()
        result = engine.extract_diff(self.old_dir, self.new_dir)

        added_paths = [f.relative_path for f in result.added_files]
        self.assertIn("added.txt", added_paths)
        self.assertEqual(len(result.deleted_files), 0)

    def test_deleted_files(self) -> None:
        """Files only in old_path are reported as deleted."""
        self._write(self.old_dir, "removed.txt", "old content")
        self._write(self.old_dir, "keep.txt", "same")
        self._write(self.new_dir, "keep.txt", "same")

        engine = DiffEngine()
        result = engine.extract_diff(self.old_dir, self.new_dir)

        deleted_paths = [f.relative_path for f in result.deleted_files]
        self.assertIn("removed.txt", deleted_paths)
        self.assertEqual(len(result.added_files), 0)

    def test_modified_files(self) -> None:
        """Files present in both with different content are reported as modified."""
        self._write(self.old_dir, "changed.txt", "version 1")
        self._write(self.new_dir, "changed.txt", "version 2")

        engine = DiffEngine()
        result = engine.extract_diff(self.old_dir, self.new_dir)

        modified_paths = [f.relative_path for f in result.modified_files]
        self.assertIn("changed.txt", modified_paths)

    def test_unchanged_files_not_reported(self) -> None:
        """Files with identical content are not in any diff list."""
        self._write(self.old_dir, "same.txt", "identical")
        self._write(self.new_dir, "same.txt", "identical")

        engine = DiffEngine()
        result = engine.extract_diff(self.old_dir, self.new_dir)

        self.assertEqual(len(result.added_files), 0)
        self.assertEqual(len(result.deleted_files), 0)
        self.assertEqual(len(result.modified_files), 0)

    def test_nested_files(self) -> None:
        """Nested directory files are discovered and compared."""
        self._write(self.old_dir, "sub/deep/file.txt", "old")
        self._write(self.new_dir, "sub/deep/file.txt", "new")

        engine = DiffEngine()
        result = engine.extract_diff(self.old_dir, self.new_dir)

        modified_paths = [f.relative_path for f in result.modified_files]
        self.assertIn("sub/deep/file.txt", modified_paths)

    def test_git_directory_ignored(self) -> None:
        """Files inside .git/ are excluded from results."""
        self._write(self.old_dir, ".git/config", "git stuff")
        self._write(self.new_dir, ".git/config", "git stuff changed")
        self._write(self.old_dir, "real.txt", "a")
        self._write(self.new_dir, "real.txt", "a")

        engine = DiffEngine()
        result = engine.extract_diff(self.old_dir, self.new_dir)

        all_paths = (
            [f.relative_path for f in result.added_files]
            + [f.relative_path for f in result.deleted_files]
            + [f.relative_path for f in result.modified_files]
        )
        for p in all_paths:
            self.assertFalse(p.startswith(".git/"), f"Should ignore .git: {p}")

    def test_empty_directories(self) -> None:
        """Empty directories produce empty results."""
        engine = DiffEngine()
        result = engine.extract_diff(self.old_dir, self.new_dir)

        self.assertEqual(len(result.added_files), 0)
        self.assertEqual(len(result.deleted_files), 0)
        self.assertEqual(len(result.modified_files), 0)


if __name__ == "__main__":
    unittest.main()
