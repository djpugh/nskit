"""File discovery with ignore-pattern support."""
from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import ClassVar

from nskit.client.diff.models import DiffMode


class FileDiscovery:
    """Discovers files in project directories with ignore-pattern support.

    Applies system exclusions (``.git/``), ``.gitignore`` patterns, and
    any extra exclusion patterns provided at construction time.

    Args:
        extra_exclusions: Additional glob patterns to exclude.
        use_gitignore: Whether to load patterns from ``.gitignore``.
    """

    SYSTEM_EXCLUSIONS: ClassVar[list[str]] = [".git/**", ".git"]

    def __init__(
        self,
        extra_exclusions: list[str] | None = None,
        use_gitignore: bool = True,
    ) -> None:
        self.extra_exclusions = extra_exclusions or []
        self.use_gitignore = use_gitignore

    def discover_files(self, project_path: Path) -> set[Path]:
        """Discover all non-excluded files under *project_path*.

        Args:
            project_path: Root directory to scan.

        Returns:
            Set of relative ``Path`` objects for each discovered file.
        """
        patterns = list(self.SYSTEM_EXCLUSIONS) + list(self.extra_exclusions)
        if self.use_gitignore:
            patterns.extend(self.load_gitignore_patterns(project_path))

        result: set[Path] = set()
        for path in project_path.rglob("*"):
            if path.is_dir():
                continue
            rel = path.relative_to(project_path)
            if not self._matches_any(rel, patterns):
                result.add(rel)
        return result

    def get_files_to_compare(
        self,
        old_path: Path,
        new_path: Path,
        diff_mode: DiffMode,
    ) -> set[Path]:
        """Return the set of relative file paths to compare.

        In ``THREE_WAY`` mode the union of both directories is returned.
        In ``TWO_WAY`` mode only files from the *new* directory are
        returned, preventing deletion of user-added files.

        Args:
            old_path: Path to the old/base project version.
            new_path: Path to the new/target project version.
            diff_mode: Comparison mode.

        Returns:
            Set of relative file paths to compare.
        """
        new_files = self.discover_files(new_path)
        if diff_mode == DiffMode.TWO_WAY:
            return new_files
        old_files = self.discover_files(old_path)
        return old_files | new_files

    def should_exclude(self, file_path: Path) -> bool:
        """Check whether a file path matches any exclusion pattern.

        Uses system exclusions and extra exclusions (does not load
        ``.gitignore`` dynamically — call ``discover_files`` for that).

        Args:
            file_path: Relative file path to check.

        Returns:
            ``True`` if the path should be excluded.
        """
        patterns = list(self.SYSTEM_EXCLUSIONS) + list(self.extra_exclusions)
        return self._matches_any(file_path, patterns)

    def load_gitignore_patterns(self, project_path: Path) -> list[str]:
        """Parse ``.gitignore`` from the project root.

        Args:
            project_path: Root directory containing ``.gitignore``.

        Returns:
            List of glob patterns extracted from the file.
        """
        gitignore = project_path / ".gitignore"
        if not gitignore.exists():
            return []

        patterns: list[str] = []
        for line in gitignore.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            patterns.append(stripped)
        return patterns

    def _matches_any(self, rel_path: Path, patterns: list[str]) -> bool:
        """Check whether *rel_path* matches any of the given patterns."""
        path_str = str(rel_path)
        for pattern in patterns:
            if fnmatch.fnmatch(path_str, pattern):
                return True
            # Also check each path component for directory patterns
            for part in rel_path.parts:
                if fnmatch.fnmatch(part, pattern):
                    return True
        return False
