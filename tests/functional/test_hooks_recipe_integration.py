"""Functional tests for hooks integration with Recipe.create().

Verifies that Recipe.create() passes the recipe instance to hooks via the
``recipe`` kwarg, and that hooks can use it to mutate recipe state (e.g.
contents) before/after rendering.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Optional, Union

from nskit.common.contextmanagers import ChDir
from nskit.mixer.components.file import File
from nskit.mixer.components.folder import Folder
from nskit.mixer.components.hook import Hook
from nskit.mixer.components.recipe import Recipe

# ---------------------------------------------------------------------------
# Module-level recording lists (avoid Pydantic model attribute issues)
# ---------------------------------------------------------------------------

_recording_calls: list = []
_introspection_names: list = []
_introspection_classes: list = []
_old_style_called: list = []


# ---------------------------------------------------------------------------
# Test hooks
# ---------------------------------------------------------------------------


class RecordingHook(Hook):
    """Hook that records what it was called with."""

    def call(self, recipe_path: Path, context: dict[str, Any], **kwargs):
        _recording_calls.append(
            {
                "recipe_path": recipe_path,
                "context": context,
                "kwargs": kwargs,
            }
        )
        return None


class ContextInjectingPreHook(Hook):
    """Pre-hook that injects a value into context."""

    inject_key: str = "hook_injected"
    inject_value: str = "from_hook"

    def call(self, recipe_path: Path, context: dict[str, Any], recipe=None):
        context[self.inject_key] = self.inject_value
        return (recipe_path, context)


class PathModifyingPreHook(Hook):
    """Pre-hook that modifies the recipe path."""

    suffix: str = "-modified"

    def call(self, recipe_path: Path, context: dict[str, Any], **kwargs):
        new_path = recipe_path.parent / (recipe_path.name + self.suffix)
        return (new_path, context)


class RecipeIntrospectingHook(Hook):
    """Hook that inspects the recipe instance."""

    def call(self, recipe_path: Path, context: dict[str, Any], recipe=None):
        if recipe is not None:
            _introspection_names.append(recipe.name)
            _introspection_classes.append(type(recipe).__name__)
        return None


class ContentMutatingPreHook(Hook):
    """Pre-hook that adds a file to the recipe's contents before rendering."""

    filename: str = "INJECTED.md"
    content: str = "# Injected by hook\n"

    def call(self, recipe_path: Path, context: dict[str, Any], recipe=None):
        if recipe is not None:
            recipe.contents.append(File(id_="injected", name=self.filename, content=self.content))
        return (recipe_path, context)


class OldStylePostHook(Hook):
    """Old-style hook that only accepts (recipe_path, context) — no kwargs."""

    def call(self, recipe_path, context):
        _old_style_called.append(True)
        return None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRecipePassesRecipeToPreHooks(unittest.TestCase):
    """Recipe.create() passes recipe=self to pre_hooks."""

    def setUp(self):
        _recording_calls.clear()

    def test_pre_hook_receives_recipe_kwarg(self):
        """Pre-hooks receive the recipe instance via kwargs."""
        hook = RecordingHook()

        recipe = Recipe(
            name="test-project",
            pre_hooks=[hook],
            contents=[File(id_="readme", name="README.md", content="# Test\n")],
        )

        with ChDir():
            recipe.create(Path.cwd())

        self.assertEqual(len(_recording_calls), 1)
        call = _recording_calls[0]
        self.assertIn("recipe", call["kwargs"])
        self.assertIs(call["kwargs"]["recipe"], recipe)


class TestRecipePassesRecipeToPostHooks(unittest.TestCase):
    """Recipe.create() passes recipe=self to post_hooks."""

    def setUp(self):
        _recording_calls.clear()

    def test_post_hook_receives_recipe_kwarg(self):
        """Post-hooks receive the recipe instance via kwargs."""
        hook = RecordingHook()

        recipe = Recipe(
            name="test-project",
            post_hooks=[hook],
            contents=[File(id_="readme", name="README.md", content="# Test\n")],
        )

        with ChDir():
            recipe.create(Path.cwd())

        self.assertEqual(len(_recording_calls), 1)
        call = _recording_calls[0]
        self.assertIn("recipe", call["kwargs"])
        self.assertIs(call["kwargs"]["recipe"], recipe)


class TestPreHookContextInjection(unittest.TestCase):
    """Pre-hooks can inject values into the template context."""

    def test_injected_context_available_in_template(self):
        """Values injected by pre-hooks are available during template rendering."""
        hook = ContextInjectingPreHook(inject_key="greeting", inject_value="hello")

        recipe = Recipe(
            name="ctx-test",
            pre_hooks=[hook],
            contents=[File(id_="out", name="output.txt", content="{{greeting}}")],
        )

        with ChDir():
            recipe.create(Path.cwd())
            content = Path("ctx-test/output.txt").read_text()
            self.assertEqual(content, "hello")


class TestPreHookPathModification(unittest.TestCase):
    """Pre-hooks can modify the output path."""

    def test_path_modified_by_pre_hook(self):
        """Pre-hook can change where the recipe is written."""
        hook = PathModifyingPreHook(suffix="-custom")

        recipe = Recipe(
            name="original",
            pre_hooks=[hook],
            contents=[File(id_="readme", name="README.md", content="# Modified path\n")],
        )

        with ChDir():
            result = recipe.create(Path.cwd())
            result_path = list(result.keys())[0]
            self.assertTrue(str(result_path).endswith("original-custom"))


class TestPreHookMutatesRecipeContents(unittest.TestCase):
    """Pre-hooks with recipe access can mutate contents before rendering."""

    def test_file_added_by_pre_hook_is_rendered(self):
        """A file added to recipe.contents by a pre-hook gets written."""
        hook = ContentMutatingPreHook(filename="ADDED.md", content="# Added\n")

        recipe = Recipe(
            name="mutate-test",
            pre_hooks=[hook],
            contents=[File(id_="readme", name="README.md", content="# Original\n")],
        )

        with ChDir():
            recipe.create(Path.cwd())
            # Original file exists
            self.assertTrue(Path("mutate-test/README.md").exists())
            # Injected file also exists
            self.assertTrue(Path("mutate-test/ADDED.md").exists())
            self.assertEqual(Path("mutate-test/ADDED.md").read_text(), "# Added\n")


class TestRecipeIntrospection(unittest.TestCase):
    """Hooks can introspect the recipe instance."""

    def setUp(self):
        _introspection_names.clear()
        _introspection_classes.clear()

    def test_hook_sees_recipe_name(self):
        """Hook can read the recipe's name field."""
        hook = RecipeIntrospectingHook()

        recipe = Recipe(
            name="my-project",
            post_hooks=[hook],
            contents=[File(id_="f", name="f.txt", content="")],
        )

        with ChDir():
            recipe.create(Path.cwd())

        self.assertEqual(_introspection_names, ["my-project"])
        self.assertEqual(_introspection_classes, ["Recipe"])


class TestBackwardsCompatibility(unittest.TestCase):
    """Old-style hooks without kwargs still work in Recipe.create()."""

    def setUp(self):
        _old_style_called.clear()

    def test_old_style_hook_works_in_recipe_create(self):
        """Old-style hook (no **kwargs) still works when recipe passes recipe kwarg."""
        hook = OldStylePostHook()

        recipe = Recipe(
            name="compat-test",
            post_hooks=[hook],
            contents=[File(id_="f", name="f.txt", content="test")],
        )

        with ChDir():
            recipe.create(Path.cwd())

        self.assertEqual(len(_old_style_called), 1)


class TestMultipleHooksOrdering(unittest.TestCase):
    """Multiple hooks execute in order."""

    def test_pre_hooks_execute_in_order(self):
        """Multiple pre-hooks execute sequentially and each sees the previous result."""
        execution_order = []

        class OrderedHook(Hook):
            index: int = 0

            def call(self, recipe_path: Path, context: dict[str, Any], **kwargs):
                execution_order.append(self.index)
                context[f"hook_{self.index}"] = True
                return (recipe_path, context)

        hooks = [OrderedHook(index=1), OrderedHook(index=2), OrderedHook(index=3)]

        recipe = Recipe(
            name="order-test",
            pre_hooks=hooks,
            contents=[File(id_="f", name="f.txt", content="")],
        )

        with ChDir():
            recipe.create(Path.cwd())

        self.assertEqual(execution_order, [1, 2, 3])

    def test_post_hooks_execute_in_order(self):
        """Multiple post-hooks execute sequentially."""
        execution_order = []

        class OrderedHook(Hook):
            index: int = 0

            def call(self, recipe_path: Path, context: dict[str, Any], **kwargs):
                execution_order.append(self.index)
                return None

        hooks = [OrderedHook(index=10), OrderedHook(index=20)]

        recipe = Recipe(
            name="order-test",
            post_hooks=hooks,
            contents=[File(id_="f", name="f.txt", content="")],
        )

        with ChDir():
            recipe.create(Path.cwd())

        self.assertEqual(execution_order, [10, 20])


class TestMixedHookStyles(unittest.TestCase):
    """Mixing old-style and new-style hooks in the same recipe."""

    def test_mixed_pre_hooks(self):
        """Old-style and new-style hooks can coexist in pre_hooks."""
        results = []

        class OldHook(Hook):
            def call(self, recipe_path, context):
                results.append("old")
                return None

        class NewHook(Hook):
            def call(self, recipe_path: Path, context: dict[str, Any], **kwargs):
                results.append(f"new:recipe={'recipe' in kwargs}")
                return None

        recipe = Recipe(
            name="mixed",
            pre_hooks=[OldHook(), NewHook()],
            contents=[File(id_="f", name="f.txt", content="")],
        )

        with ChDir():
            recipe.create(Path.cwd())

        self.assertEqual(results, ["old", "new:recipe=True"])

    def test_mixed_post_hooks(self):
        """Old-style and new-style hooks can coexist in post_hooks."""
        results = []

        class OldHook(Hook):
            def call(self, recipe_path, context):
                results.append("old")
                return None

        class NewHook(Hook):
            def call(self, recipe_path: Path, context: dict[str, Any], recipe=None):
                results.append(f"new:recipe={recipe is not None}")
                return None

        recipe = Recipe(
            name="mixed",
            post_hooks=[OldHook(), NewHook()],
            contents=[File(id_="f", name="f.txt", content="")],
        )

        with ChDir():
            recipe.create(Path.cwd())

        self.assertEqual(results, ["old", "new:recipe=True"])


if __name__ == "__main__":
    unittest.main()
