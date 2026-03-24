"""Comprehensive tests for 3-way merge behavior."""
import pytest
import subprocess
from pathlib import Path

from nskit.mixer.utils import GitUtils
from nskit.mixer.update import DiffMode


@pytest.fixture
def git_repo_with_files(tmp_path):
    """Create a git repo with initial files."""
    repo = tmp_path / "repo"
    repo.mkdir()
    
    # Initialize git
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True, check=True)
    
    return repo


class TestThreeWayMerge:
    """Test 3-way merge behavior."""

    def test_merge_no_conflicts(self, git_repo_with_files):
        """Test 3-way merge with no conflicts."""
        repo = git_repo_with_files
        
        # Create content
        base_content = "line1\nline2\nline3\n"
        user_content = "line1_modified_by_user\nline2\nline3\n"
        template_content = "line1\nline2\nline3_modified_by_recipe\n"
        
        # Perform 3-way merge
        git_utils = GitUtils(repo)
        merged_content, has_conflicts = git_utils.merge_file(
            base_content, user_content, template_content
        )
        
        # Should merge cleanly
        assert not has_conflicts
        assert "line1_modified_by_user" in merged_content
        assert "line3_modified_by_recipe" in merged_content

    def test_merge_with_conflicts(self, git_repo_with_files):
        """Test 3-way merge with conflicts."""
        repo = git_repo_with_files
        
        # Create content
        base_content = "line1\nline2\nline3\n"
        user_content = "line1\nline2_user_change\nline3\n"
        template_content = "line1\nline2_recipe_change\nline3\n"
        
        # Perform 3-way merge
        git_utils = GitUtils(repo)
        merged_content, has_conflicts = git_utils.merge_file(
            base_content, user_content, template_content
        )
        
        # Should have conflicts
        assert has_conflicts
        assert "<<<<<<" in merged_content
        assert "line2_user_change" in merged_content
        assert "line2_recipe_change" in merged_content

    def test_merge_user_added_lines(self, git_repo_with_files):
        """Test merge preserves user-added lines."""
        repo = git_repo_with_files
        
        # Create content
        base_content = "line1\nline2\n"
        user_content = "line1\nline2\nuser_added_line\n"
        template_content = "line1_updated\nline2\n"
        
        # Perform 3-way merge
        git_utils = GitUtils(repo)
        merged_content, has_conflicts = git_utils.merge_file(
            base_content, user_content, template_content
        )
        
        # Should preserve user addition
        assert not has_conflicts
        assert "user_added_line" in merged_content
        assert "line1_updated" in merged_content

    def test_merge_recipe_added_lines(self, git_repo_with_files):
        """Test merge includes recipe-added lines."""
        repo = git_repo_with_files
        
        # Create content
        base_content = "line1\nline2\n"
        user_content = "line1\nline2\n"
        template_content = "line1\nline2\nrecipe_added_line\n"
        
        # Perform 3-way merge
        git_utils = GitUtils(repo)
        merged_content, has_conflicts = git_utils.merge_file(
            base_content, user_content, template_content
        )
        
        # Should include recipe addition
        assert not has_conflicts
        assert "recipe_added_line" in merged_content

    def test_merge_both_deleted_same_line(self, git_repo_with_files):
        """Test merge when both deleted same line."""
        repo = git_repo_with_files
        
        # Create content
        base_content = "line1\nline2\nline3\n"
        user_content = "line1\nline3\n"
        template_content = "line1\nline3\n"
        
        # Perform 3-way merge
        git_utils = GitUtils(repo)
        merged_content, has_conflicts = git_utils.merge_file(
            base_content, user_content, template_content
        )
        
        # Should merge cleanly (both made same change)
        assert not has_conflicts
        assert "line2" not in merged_content

    def test_merge_complex_scenario(self, git_repo_with_files):
        """Test complex merge scenario with multiple changes."""
        repo = git_repo_with_files
        
        # Create content
        base_content = "header\nline1\nline2\nline3\nfooter\n"
        user_content = "header\nline1_user\nline2\nline3\nuser_addition\nfooter\n"
        template_content = "header_updated\nline1\nline2_recipe\nline3\nfooter\n"
        
        # Perform 3-way merge
        git_utils = GitUtils(repo)
        merged_content, has_conflicts = git_utils.merge_file(
            base_content, user_content, template_content
        )
        
        # Check results
        assert "header_updated" in merged_content  # Recipe change
        assert "line1_user" in merged_content  # User change
        assert "user_addition" in merged_content  # User addition
        # line2 will have conflict
        assert has_conflicts

    def test_merge_empty_files(self, git_repo_with_files):
        """Test merge with empty files."""
        repo = git_repo_with_files
        
        # Create content
        base_content = ""
        user_content = "user_content\n"
        template_content = "recipe_content\n"
        
        # Perform 3-way merge
        git_utils = GitUtils(repo)
        merged_content, has_conflicts = git_utils.merge_file(
            base_content, user_content, template_content
        )
        
        # Both additions should be present
        assert "user_content" in merged_content
        assert "recipe_content" in merged_content

    def test_merge_preserves_whitespace(self, git_repo_with_files):
        """Test merge preserves whitespace correctly."""
        repo = git_repo_with_files
        
        # Create content with specific whitespace
        base_content = "line1\n  indented\nline3\n"
        user_content = "line1_modified\n  indented\nline3\n"
        template_content = "line1\n  indented\nline3_modified\n"
        
        # Perform 3-way merge
        git_utils = GitUtils(repo)
        merged_content, has_conflicts = git_utils.merge_file(
            base_content, user_content, template_content
        )
        
        # Should preserve indentation
        assert not has_conflicts
        assert "  indented" in merged_content
        assert "line1_modified" in merged_content
        assert "line3_modified" in merged_content


class TestDiffModes:
    """Test different diff modes."""

    def test_two_way_diff(self, tmp_path):
        """Test 2-way diff mode."""
        from nskit.mixer.update import DiffEngine, DiffMode
        
        old_dir = tmp_path / "old"
        old_dir.mkdir()
        (old_dir / "file1.txt").write_text("old content")
        
        new_dir = tmp_path / "new"
        new_dir.mkdir()
        (new_dir / "file1.txt").write_text("new content")
        (new_dir / "file2.txt").write_text("added file")
        
        engine = DiffEngine()
        result = engine.extract_diff(old_dir, new_dir, DiffMode.TWO_WAY)
        
        assert len(result.modified_files) == 1
        assert len(result.added_files) == 1
        assert result.modified_files[0].relative_path == "file1.txt"
        assert result.added_files[0].relative_path == "file2.txt"

    def test_three_way_diff(self, tmp_path):
        """Test 3-way diff mode."""
        from nskit.mixer.update import DiffEngine, DiffMode
        
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        (base_dir / "file1.txt").write_text("base content")
        
        new_dir = tmp_path / "new"
        new_dir.mkdir()
        (new_dir / "file1.txt").write_text("new content")
        
        engine = DiffEngine()
        result = engine.extract_diff(base_dir, new_dir, DiffMode.THREE_WAY)
        
        assert len(result.modified_files) == 1
        assert result.modified_files[0].relative_path == "file1.txt"
