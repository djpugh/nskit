"""Reusable test harness for recipes.

Generic checks any downstream recipe pack can run against its recipes without
re-implementing the boilerplate. The machinery is recipe-agnostic; callers
supply only the sample inputs needed to construct each recipe.

Typical use in a downstream ``conftest``/test module::

    import pytest
    from nskit.mixer.testing import check_recipe, iter_entrypoint_recipes

    INPUTS = {"python_package": {"name": "svc", "repo": {...}}, ...}

    @pytest.mark.parametrize("name", list_recipes("paebbl.nskitchen.recipes"))
    def test_recipe(name):
        result = check_recipe(name, INPUTS[name], entrypoint="paebbl.nskitchen.recipes")
        assert result.ok, result.summary()

The harness never asserts on its own — it returns a :class:`RecipeCheckResult`
so the caller decides which findings are fatal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import jinja2

from nskit.common.contextmanagers import ChDir
from nskit.common.extensions import get_extension_names
from nskit.mixer.components import File, Folder, Recipe
from nskit.mixer.components.recipe import RECIPE_ENTRYPOINT
from nskit.mixer.utilities import Resource


def list_recipes(entrypoint: str = RECIPE_ENTRYPOINT) -> list[str]:
    """Return the names of every recipe registered under ``entrypoint``.

    Use this to parametrize tests so newly-registered recipes are covered
    automatically rather than needing a hand-maintained list.
    """
    return sorted(get_extension_names(entrypoint))


def iter_files(contents) -> list[File]:
    """Flatten a recipe/folder ``contents`` tree into its ``File`` leaves."""
    files: list[File] = []
    for item in contents:
        if isinstance(item, File):
            files.append(item)
        elif isinstance(item, Folder):
            files.extend(iter_files(item.contents))
    return files


@dataclass
class RecipeCheckResult:
    """Outcome of running the harness over a single recipe."""

    recipe: str
    unresolved_resources: list[str] = field(default_factory=list)
    template_errors: list[str] = field(default_factory=list)
    duplicate_paths: list[str] = field(default_factory=list)
    construction_error: str | None = None
    render_error: str | None = None
    file_count: int = 0

    @property
    def ok(self) -> bool:
        """True when no fatal problem was found."""
        return not (
            self.construction_error
            or self.render_error
            or self.unresolved_resources
            or self.template_errors
            or self.duplicate_paths
        )

    def summary(self) -> str:
        """Human-readable multi-line summary of all findings (for assert messages)."""
        lines = [f"recipe {self.recipe!r}: {'OK' if self.ok else 'FAILED'} ({self.file_count} files)"]
        if self.construction_error:
            lines.append(f"  construction error: {self.construction_error}")
        if self.render_error:
            lines.append(f"  render error: {self.render_error}")
        for r in self.unresolved_resources:
            lines.append(f"  unresolved resource: {r}")
        for e in self.template_errors:
            lines.append(f"  template parse error: {e}")
        for d in self.duplicate_paths:
            lines.append(f"  duplicate output path: {d}")
        return "\n".join(lines)


def _walk_paths(tree: dict, seen: set, duplicates: list) -> None:
    for path, value in tree.items():
        if isinstance(value, dict):
            _walk_paths(value, seen, duplicates)
        else:
            key = str(path)
            if key in seen:
                duplicates.append(key)
            seen.add(key)


def check_recipe(
    recipe: str | type | Recipe,
    inputs: dict[str, Any] | None = None,
    *,
    entrypoint: str = RECIPE_ENTRYPOINT,
    parse_templates: bool = True,
) -> RecipeCheckResult:
    """Run the standard battery of structural checks against a recipe.

    The recipe may be given as an entry-point name, a class, or an instance.
    ``inputs`` provides the construction kwargs (ignored if an instance is
    passed). Checks performed:

    * the recipe constructs from ``inputs``;
    * every ``File`` backed by a :class:`Resource` resolves to a loadable
      template;
    * every template parses as Jinja (catches unguarded ``${{ }}`` etc.);
    * ``dryrun`` renders without raising;
    * no two files render to the same output path.

    Returns a :class:`RecipeCheckResult`; never raises for recipe problems
    (only for genuinely broken usage). The caller asserts on ``.ok``.
    """
    inputs = inputs or {}
    name = (
        recipe
        if isinstance(recipe, str)
        else getattr(recipe, "extension_name", None) or getattr(recipe, "__name__", recipe.__class__.__name__)
    )
    result = RecipeCheckResult(recipe=str(name))

    # --- construct -------------------------------------------------------
    try:
        if isinstance(recipe, str):
            instance = Recipe.load(recipe, entrypoint=entrypoint, **inputs)
        elif isinstance(recipe, type):
            instance = recipe(**inputs)
        else:
            instance = recipe
    except Exception as exc:  # noqa: BLE001 - report, don't crash the suite
        result.construction_error = f"{type(exc).__name__}: {exc}"
        return result

    # --- resource resolution + template parsing --------------------------
    # autoescape is irrelevant here (we only ``parse`` for syntax, never render
    # untrusted output) but set it so the env is safe-by-construction.
    env = jinja2.Environment(autoescape=jinja2.select_autoescape()) if parse_templates else None
    for f in iter_files(instance.contents):
        if not isinstance(f.content, Resource):
            continue
        try:
            source = f.content.load()
        except (FileNotFoundError, ModuleNotFoundError, OSError) as exc:
            result.unresolved_resources.append(f"{f.content} ({exc})")
            continue
        if env is not None:
            try:
                env.parse(source)
            except jinja2.TemplateSyntaxError as exc:
                result.template_errors.append(f"{f.content}: {exc}")

    # --- dryrun + duplicate-path detection -------------------------------
    try:
        with ChDir():
            tree = instance.dryrun()
        seen: set = set()
        duplicates: list[str] = []
        _walk_paths(tree, seen, duplicates)
        result.duplicate_paths = duplicates
        result.file_count = len(seen)
    except Exception as exc:  # noqa: BLE001
        result.render_error = f"{type(exc).__name__}: {exc}"

    return result


def check_recipes(
    inputs_by_recipe: dict[str, dict[str, Any]],
    *,
    entrypoint: str = RECIPE_ENTRYPOINT,
    require_all_registered: bool = True,
) -> dict[str, RecipeCheckResult]:
    """Run :func:`check_recipe` over every recipe in ``inputs_by_recipe``.

    When ``require_all_registered`` is True, any recipe registered under
    ``entrypoint`` but missing from ``inputs_by_recipe`` is reported as a
    construction error — so a newly-added recipe with no sample inputs fails
    loudly rather than going silently untested.
    """
    results: dict[str, RecipeCheckResult] = {}
    if require_all_registered:
        for missing in set(list_recipes(entrypoint)) - set(inputs_by_recipe):
            r = RecipeCheckResult(recipe=missing)
            r.construction_error = "registered recipe has no sample inputs in the test suite — add it so it is covered"
            results[missing] = r
    for name, inputs in inputs_by_recipe.items():
        results[name] = check_recipe(name, inputs, entrypoint=entrypoint)
    return results
