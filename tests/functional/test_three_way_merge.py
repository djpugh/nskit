"""Comprehensive tests for 3-way merge behaviour."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from nskit.client.utils.git import GitUtils
from nskit.common.models.diff import DiffMode


@pytest.mark.usefixtures("git_repo")
class TestThreeWayMerge(unittest.TestCase):
    """Test 3-way merge behaviour."""

    def test_merge_no_conflicts(self):
        """Test 3-way merge with no conflicts."""
        base_content = "line1\nline2\nline3\n"
        user_content = "line1_modified_by_user\nline2\nline3\n"
        template_content = "line1\nline2\nline3_modified_by_recipe\n"

        git_utils = GitUtils(self.git_repo)
        merged_content, has_conflicts = git_utils.merge_file(base_content, user_content, template_content)

        self.assertFalse(has_conflicts)
        self.assertIn("line1_modified_by_user", merged_content)
        self.assertIn("line3_modified_by_recipe", merged_content)

    def test_merge_with_conflicts(self):
        """Test 3-way merge with conflicts."""
        base_content = "line1\nline2\nline3\n"
        user_content = "line1\nline2_user_change\nline3\n"
        template_content = "line1\nline2_recipe_change\nline3\n"

        git_utils = GitUtils(self.git_repo)
        merged_content, has_conflicts = git_utils.merge_file(base_content, user_content, template_content)

        self.assertTrue(has_conflicts)
        self.assertIn("<<<<<<", merged_content)
        self.assertIn("line2_user_change", merged_content)
        self.assertIn("line2_recipe_change", merged_content)

    def test_merge_user_added_lines(self):
        """Test merge preserves user-added lines."""
        base_content = "line1\nline2\n"
        user_content = "line1\nline2\nuser_added_line\n"
        template_content = "line1_updated\nline2\n"

        git_utils = GitUtils(self.git_repo)
        merged_content, has_conflicts = git_utils.merge_file(base_content, user_content, template_content)

        self.assertFalse(has_conflicts)
        self.assertIn("user_added_line", merged_content)
        self.assertIn("line1_updated", merged_content)

    def test_merge_recipe_added_lines(self):
        """Test merge includes recipe-added lines."""
        base_content = "line1\nline2\n"
        user_content = "line1\nline2\n"
        template_content = "line1\nline2\nrecipe_added_line\n"

        git_utils = GitUtils(self.git_repo)
        merged_content, has_conflicts = git_utils.merge_file(base_content, user_content, template_content)

        self.assertFalse(has_conflicts)
        self.assertIn("recipe_added_line", merged_content)

    def test_merge_both_deleted_same_line(self):
        """Test merge when both deleted same line."""
        base_content = "line1\nline2\nline3\n"
        user_content = "line1\nline3\n"
        template_content = "line1\nline3\n"

        git_utils = GitUtils(self.git_repo)
        merged_content, has_conflicts = git_utils.merge_file(base_content, user_content, template_content)

        self.assertFalse(has_conflicts)
        self.assertNotIn("line2", merged_content)

    def test_merge_complex_scenario(self):
        """Test complex merge scenario with multiple changes."""
        base_content = "header\nline1\nline2\nline3\nfooter\n"
        user_content = "header\nline1_user\nline2\nline3\nuser_addition\nfooter\n"
        template_content = "header_updated\nline1\nline2_recipe\nline3\nfooter\n"

        git_utils = GitUtils(self.git_repo)
        merged_content, has_conflicts = git_utils.merge_file(base_content, user_content, template_content)

        self.assertIn("header_updated", merged_content)
        self.assertIn("line1_user", merged_content)
        self.assertIn("user_addition", merged_content)
        self.assertTrue(has_conflicts)

    def test_merge_empty_files(self):
        """Test merge with empty files."""
        base_content = ""
        user_content = "user_content\n"
        template_content = "recipe_content\n"

        git_utils = GitUtils(self.git_repo)
        merged_content, has_conflicts = git_utils.merge_file(base_content, user_content, template_content)

        self.assertIn("user_content", merged_content)
        self.assertIn("recipe_content", merged_content)

    def test_merge_preserves_whitespace(self):
        """Test merge preserves whitespace correctly."""
        base_content = "line1\n  indented\nline3\n"
        user_content = "line1_modified\n  indented\nline3\n"
        template_content = "line1\n  indented\nline3_modified\n"

        git_utils = GitUtils(self.git_repo)
        merged_content, has_conflicts = git_utils.merge_file(base_content, user_content, template_content)

        self.assertFalse(has_conflicts)
        self.assertIn("  indented", merged_content)
        self.assertIn("line1_modified", merged_content)
        self.assertIn("line3_modified", merged_content)


class TestDiffModes(unittest.TestCase):
    """Test different diff modes."""

    def test_two_way_diff(self):
        """Test 2-way diff mode."""
        from nskit.client.diff import DiffEngine
        from nskit.common.models.diff import DiffMode

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            old_dir = tmp_path / "old"
            old_dir.mkdir()
            (old_dir / "file1.txt").write_text("old content")

            new_dir = tmp_path / "new"
            new_dir.mkdir()
            (new_dir / "file1.txt").write_text("new content")
            (new_dir / "file2.txt").write_text("added file")

            engine = DiffEngine()
            result = engine.extract_diff(old_dir, new_dir, DiffMode.TWO_WAY)

            self.assertEqual(len(result.modified_files), 1)
            self.assertEqual(len(result.added_files), 1)
            self.assertEqual(result.modified_files[0].relative_path, "file1.txt")
            self.assertEqual(result.added_files[0].relative_path, "file2.txt")

    def test_three_way_diff(self):
        """Test 3-way diff mode."""
        from nskit.client.diff import DiffEngine
        from nskit.common.models.diff import DiffMode

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            base_dir = tmp_path / "base"
            base_dir.mkdir()
            (base_dir / "file1.txt").write_text("base content")

            new_dir = tmp_path / "new"
            new_dir.mkdir()
            (new_dir / "file1.txt").write_text("new content")

            engine = DiffEngine()
            result = engine.extract_diff(base_dir, new_dir, DiffMode.THREE_WAY)

            self.assertEqual(len(result.modified_files), 1)
            self.assertEqual(result.modified_files[0].relative_path, "file1.txt")


if __name__ == "__main__":
    unittest.main()
