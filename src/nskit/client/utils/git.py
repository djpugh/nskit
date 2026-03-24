"""Git utilities for recipe operations."""
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple


class GitStatusError(Exception):
    """Raised when Git repository is in an invalid state."""

    def __init__(self, reason: str):
        super().__init__(f"Git repository is not ready: {reason}")


class GitUtils:
    """Utilities for Git operations using git commands."""

    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = project_path or Path.cwd()

    def is_git_repository(self) -> bool:
        """Check if directory is a Git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        if not self.is_git_repository():
            return False

        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return bool(result.stdout.strip())
        except subprocess.CalledProcessError:
            return False

    def get_current_commit(self) -> Optional[str]:
        """Get current commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def merge_file(
        self,
        base_content: str,
        user_content: str,
        template_content: str,
        user_label: str = "USER CHANGES",
        base_label: str = "BASE VERSION",
        template_label: str = "TEMPLATE CHANGES",
    ) -> Tuple[str, bool]:
        """Perform 3-way merge using git merge-file.
        
        Args:
            base_content: Original content (common ancestor)
            user_content: User's version
            template_content: Template's version
            user_label: Label for user changes in conflict markers
            base_label: Label for base version
            template_label: Label for template changes
            
        Returns:
            Tuple of (merged_content, has_conflicts)
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create temporary files for 3-way merge
            base_file = temp_path / "base"
            user_file = temp_path / "user"
            template_file = temp_path / "template"

            base_file.write_text(base_content, encoding="utf-8")
            user_file.write_text(user_content, encoding="utf-8")
            template_file.write_text(template_content, encoding="utf-8")

            try:
                # Run git merge-file
                result = subprocess.run(
                    [
                        "git",
                        "merge-file",
                        "-L", user_label,
                        "-L", base_label,
                        "-L", template_label,
                        str(user_file),
                        str(base_file),
                        str(template_file),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                merged_content = user_file.read_text(encoding="utf-8")
                has_conflicts = result.returncode != 0

                return merged_content, has_conflicts

            except Exception as e:
                raise RuntimeError(f"Git merge-file failed: {e}")

    def diff_files(self, old_path: Path, new_path: Path) -> str:
        """Get diff between two files using git diff.
        
        Args:
            old_path: Path to old file
            new_path: Path to new file
            
        Returns:
            Diff output
        """
        try:
            result = subprocess.run(
                [
                    "git",
                    "diff",
                    "--no-index",
                    str(old_path),
                    str(new_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.stdout
        except Exception as e:
            raise RuntimeError(f"Git diff failed: {e}")
