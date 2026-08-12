"""Hook component."""

import inspect
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel


class Hook(ABC, BaseModel):
    """Hook component.

    Hooks receive the recipe path and context, and optionally the recipe
    instance itself. The ``recipe`` kwarg enables pre-write hooks to mutate
    the recipe's ``contents`` before rendering.

    Backwards-compatible: existing hooks that define
    ``call(self, recipe_path, context)`` without **kwargs continue to work —
    the recipe kwarg is only forwarded if the hook's ``call`` signature accepts it.
    """

    @abstractmethod
    def call(self, recipe_path: Path, context: dict[str, Any], **kwargs) -> Optional[tuple[Path, dict]]:
        """Execute the hook logic.

        Args:
            recipe_path: Path where the recipe will be (pre) or was (post) written.
            context: Template rendering context (all recipe fields + properties).
            **kwargs: Additional keyword arguments. Currently passes ``recipe``
                (the Recipe instance) when called from ``Recipe.create()``.
                Hooks that don't need the recipe can ignore it via **kwargs.

        Returns:
            None to keep path/context unchanged, or ``(recipe_path, context)`` tuple.
        """
        raise NotImplementedError()

    def __call__(self, recipe_path: Path, context: dict[str, Any], **kwargs) -> tuple[Path, dict]:
        """Call the hook and return tuple (recipe_path, context).

        Inspects the ``call`` method signature to determine whether to forward
        kwargs (like ``recipe``). This ensures backwards compatibility with
        existing hooks that only accept ``(recipe_path, context)``.
        """
        sig = inspect.signature(self.call)
        params = sig.parameters

        # Forward kwargs only if call() accepts **kwargs or explicitly declares the kwarg names
        accepts_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
        if accepts_kwargs:
            hook_result = self.call(recipe_path, context, **kwargs)
        else:
            # Check which specific kwargs the method accepts
            forward = {k: v for k, v in kwargs.items() if k in params}
            hook_result = self.call(recipe_path, context, **forward)

        if hook_result:
            recipe_path, context = hook_result
        return recipe_path, context
