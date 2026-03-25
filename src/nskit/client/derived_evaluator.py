"""Derived field evaluator using Jinja2 template expressions."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Callable, ClassVar

from jinja2 import Environment

from nskit.client.context import ContextProvider
from nskit.mixer.utilities import JINJA_ENVIRONMENT_FACTORY

if TYPE_CHECKING:
    pass


class DerivedFieldEvaluator:
    """Evaluates derived field default expressions.

    Reuses the existing ``JINJA_ENVIRONMENT_FACTORY`` from
    ``nskit.mixer.utilities``, adding built-in filters for common
    transformations. This keeps template behaviour consistent with the
    mixer's own Jinja2 rendering.

    Supports:
        - Previously collected field values: ``{{ project_name }}``
        - Built-in filters: ``{{ project_name | slugify }}``
        - Context helpers: ``{{ ctx.username }}``

    Args:
        context_provider: Optional provider for built-in context values.
    """

    BUILTIN_FILTERS: ClassVar[dict[str, Callable[..., str]]] = {
        "slugify": lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-"),
        "lower": str.lower,
        "upper": str.upper,
        "title": str.title,
        "snake_case": lambda s: re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_"),
        "camel_case": lambda s: "".join(w.title() for w in re.split(r"[^a-zA-Z0-9]+", s) if w),
    }

    def __init__(self, context_provider: ContextProvider | None = None) -> None:
        self.context_provider = context_provider
        self._env: Environment | None = None

    @property
    def jinja_env(self) -> Environment:
        """Get the Jinja2 environment with built-in filters registered.

        Returns:
            Configured Jinja2 ``Environment`` instance.
        """
        if self._env is None:
            self._env = JINJA_ENVIRONMENT_FACTORY.environment
            for name, func in self.BUILTIN_FILTERS.items():
                if name not in self._env.filters:
                    self._env.filters[name] = func
        return self._env

    def evaluate(self, template: str, collected_values: dict[str, Any]) -> Any:
        """Evaluate a template expression against collected values and context.

        Args:
            template: Jinja2 template string to evaluate.
            collected_values: Previously collected field values.

        Returns:
            The rendered template result.
        """
        context = self._build_template_context(collected_values)
        tpl = self.jinja_env.from_string(template)
        return tpl.render(context)

    def _build_template_context(self, collected_values: dict[str, Any]) -> dict[str, Any]:
        """Merge collected values with context provider values.

        Context provider values are placed under the ``ctx`` namespace.

        Args:
            collected_values: Previously collected field values.

        Returns:
            Combined template context dictionary.
        """
        context: dict[str, Any] = dict(collected_values)
        if self.context_provider is not None:
            context["ctx"] = self.context_provider.get_context()
        return context
