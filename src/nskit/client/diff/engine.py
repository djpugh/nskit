"""Diff engine for recipe updates."""
import subprocess
from pathlib import Path
from typing import Set

from nskit.client.diff.models import DiffMode, DiffResult, DiffType, FileDiff


class DiffEngine:
    """Engine for computing diffs between recipe versions."""

    def __init__(self, context_lines: int = 3):
        """Initialize diff engine.
        
        Args:
            context_lines: Number of context lines for diffs
        """
        self.context_lines = context_lines

    def extract_diff(
        self, old_path: Path, new_path: Path, diff_mode: DiffMode = DiffMode.TWO_WAY
    ) -> DiffResult:
        """Extract differences between two paths.
        
        Args:
            old_path: Path to old version
            new_path: Path to new version
            diff_mode: Diff mode (2-way or 3-way)
            
        Returns:
            Structured diff result
        """
        # Get list of all files in both directories
        old_files = self._get_files(old_path)
        new_files = self._get_files(new_path)

        added = []
        deleted = []
        modified = []

        # Find added files
        for file in new_files - old_files:
            added.append(
                FileDiff(
                    path=new_path / file,
                    relative_path=file,
                    diff_type=DiffType.ADDED,
                )
            )

        # Find deleted files
        for file in old_files - new_files:
            deleted.append(
                FileDiff(
                    path=old_path / file,
                    relative_path=file,
                    diff_type=DiffType.DELETED,
                )
            )

        # Find modified files
        for file in old_files & new_files:
            old_file = old_path / file
            new_file = new_path / file

            if self._files_differ(old_file, new_file):
                modified.append(
                    FileDiff(
                        path=new_file,
                        relative_path=file,
                        diff_type=DiffType.MODIFIED,
                    )
                )

        return DiffResult(
            added_files=added,
            deleted_files=deleted,
            modified_files=modified,
        )

    def _get_files(self, path: Path) -> Set[str]:
        """Get all files in directory recursively."""
        files = set()
        for item in path.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(path).as_posix()
                # Skip common ignore patterns
                if not self._should_ignore(rel_path):
                    files.add(rel_path)
        return files

    def _should_ignore(self, path: str) -> bool:
        """Check if path should be ignored."""
        ignore_patterns = [
            ".git/",
            "__pycache__/",
            ".pyc",
            ".pyo",
            ".DS_Store",
            ".recipe/",
        ]
        return any(pattern in path for pattern in ignore_patterns)

    def _files_differ(self, file1: Path, file2: Path) -> bool:
        """Check if two files differ."""
        try:
            # Use git diff for comparison
            result = subprocess.run(
                ["git", "diff", "--no-index", "--quiet", str(file1), str(file2)],
                capture_output=True,
            )
            return result.returncode != 0
        except Exception:
            # Fallback to byte comparison
            return file1.read_bytes() != file2.read_bytes()
