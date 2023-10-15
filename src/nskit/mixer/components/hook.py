"""Hook component."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel


class Hook(ABC, BaseModel):
    """Hook component."""

    @abstractmethod
    def call(self, recipe_path: Path, context: Dict[str, Any]) -> Optional[Tuple[str, Path, Dict]]:
        """Return None or tuple (recipe_path, context)."""
        raise NotImplementedError()

    def __call__(self, recipe_path: Path, context: Dict[str, Any]) -> Tuple[str, Path, Dict]:
        """Call the hook and return tuple (recipe_path, context)."""
        hook_result = self.call(recipe_path, context)
        if hook_result:
            recipe_path, context = hook_result
        return recipe_path, context
