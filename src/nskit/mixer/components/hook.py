from abc import ABC
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from pydantic import BaseModel


class Hook(ABC, BaseModel):

    def call(self, recipe_name: str, recipe_path: Path, context: Dict[str, Any]) -> Optional[Tuple[str, Path, Dict]]:
        """Return None or tuple (recipe_name, recipe_path, context)"""
        raise NotImplementedError()

    def __call__(self, recipe_name: str, recipe_path: Path, context: Dict[str, Any]) -> Tuple[str, Path, Dict]:
        """Call the hook and return tuple (recipe_name, recipe_path, context)"""
        hook_result = self.call(recipe_name, recipe_path, context)
        if hook_result:
            recipe_name, recipe_path, context = hook_result
        return recipe_name, recipe_path, context
