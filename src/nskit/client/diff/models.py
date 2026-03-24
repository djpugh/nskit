"""Diff models for recipe updates."""
from enum import Enum
from pathlib import Path
from typing import List, Set

from pydantic import BaseModel, Field


class DiffMode(str, Enum):
    """Diff mode for updates."""
    TWO_WAY = "2way"
    THREE_WAY = "3way"


class DiffType(str, Enum):
    """Type of file change."""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"


class LineChange(BaseModel):
    """Represents a line change in a diff."""
    line_number: int
    content: str
    change_type: str  # '+', '-', ' '


class FileDiff(BaseModel):
    """Represents differences in a single file."""
    path: Path
    relative_path: str = ""
    diff_type: DiffType
    changes: List[LineChange] = Field(default_factory=list)
    has_conflicts: bool = False


class DiffResult(BaseModel):
    """Result of diff operation."""
    files: List[FileDiff] = Field(default_factory=list)
    added_files: List[FileDiff] = Field(default_factory=list)
    modified_files: List[FileDiff] = Field(default_factory=list)
    deleted_files: List[FileDiff] = Field(default_factory=list)


class MergeResult(BaseModel):
    """Result of merge operation."""
    clean_merges: List[str] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

    def get_clean_merge_files(self) -> Set[str]:
        """Get set of cleanly merged files."""
        return set(self.clean_merges)
