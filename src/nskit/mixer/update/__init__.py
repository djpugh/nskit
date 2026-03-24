"""Mixer update module (moved to nskit.client.diff)."""
# Backward compatibility - re-export from new location
from nskit.client.diff import DiffEngine
from nskit.client.diff.models import (
    DiffMode,
    DiffResult,
    DiffType,
    FileDiff,
    MergeResult,
)

__all__ = [
    "DiffEngine",
    "DiffMode",
    "DiffResult",
    "DiffType",
    "FileDiff",
    "MergeResult",
]
