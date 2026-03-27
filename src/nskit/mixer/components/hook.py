"""Hook component."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel


class Hook(ABC, BaseModel):
    """Hook component."""

    @abstractmethod
    def call(self, recipe_path: Path, context: dict[str, Any]) -> Optional[tuple[str, Path, dict]]:
        """Return None or tuple (recipe_path, context)."""
        raise NotImplementedError()

    def __call__(self, recipe_path: Path, context: dict[str, Any]) -> tuple[str, Path, dict]:
        """Call the hook and return tuple (recipe_path, context)."""
        hook_result = self.call(recipe_path, context)
        if hook_result:
            recipe_path, context = hook_result
        return recipe_path, context
