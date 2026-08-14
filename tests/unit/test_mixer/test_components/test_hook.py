"""Tests for Hook component including kwargs forwarding logic."""

import unittest
from pathlib import Path
from typing import Any, Optional
from unittest.mock import patch

from nskit.mixer.components.hook import Hook


class HookTestCase(unittest.TestCase):
    def setUp(self):
        self._patch = patch.object(Hook, "__abstractmethods__", set())
        self._patch.start()

    def tearDown(self) -> None:
        self._patch.stop()

    def test_call(self):
        with self.assertRaises(NotImplementedError):
            Hook().call(None, None)

    def test__call__no_result(self):
        class TestHook(Hook):
            def call(self, recipe_path, context):
                return None

        t = TestHook()
        self.assertEqual(t(1, 2), (1, 2))

    def test__call__result(self):
        class TestHook(Hook):
            def call(self, recipe_path, context):
                return (3, 4)

        t = TestHook()
        self.assertEqual(t(1, 2), (3, 4))


class HookKwargsForwardingTestCase(unittest.TestCase):
    """Tests for kwargs forwarding behaviour in Hook.__call__."""

    def test_kwargs_forwarded_when_call_accepts_var_keyword(self):
        """Hook with **kwargs in call() receives all forwarded kwargs."""

        class KwargsHook(Hook):
            def call(self, recipe_path: Path, context: dict[str, Any], **kwargs):
                return (recipe_path, {**context, "received_kwargs": kwargs})

        hook = KwargsHook()
        path = Path("/tmp/test")
        ctx = {"key": "value"}
        result_path, result_ctx = hook(path, ctx, recipe="mock_recipe", extra="data")

        self.assertEqual(result_path, path)
        self.assertEqual(result_ctx["received_kwargs"]["recipe"], "mock_recipe")
        self.assertEqual(result_ctx["received_kwargs"]["extra"], "data")

    def test_kwargs_not_forwarded_when_call_has_no_var_keyword(self):
        """Hook without **kwargs in call() does not receive unknown kwargs."""
        received_args = {}

        class SimpleHook(Hook):
            def call(self, recipe_path: Path, context: dict[str, Any]):
                received_args["path"] = recipe_path
                received_args["context"] = context
                return None

        hook = SimpleHook()
        path = Path("/tmp/test")
        ctx = {"key": "value"}
        result_path, result_ctx = hook(path, ctx, recipe="mock_recipe")

        self.assertEqual(result_path, path)
        self.assertEqual(result_ctx, ctx)
        # Confirm only the positional args were received
        self.assertEqual(received_args["path"], path)
        self.assertEqual(received_args["context"], ctx)

    def test_specific_kwarg_forwarded_when_explicitly_declared(self):
        """Hook with explicitly declared 'recipe' param receives it without **kwargs."""
        received = {}

        class RecipeAwareHook(Hook):
            def call(self, recipe_path: Path, context: dict[str, Any], recipe=None):
                received["recipe"] = recipe
                return (recipe_path, context)

        hook = RecipeAwareHook()
        path = Path("/tmp/test")
        ctx = {}
        hook(path, ctx, recipe="my_recipe", other="ignored")

        self.assertEqual(received["recipe"], "my_recipe")

    def test_only_matching_kwargs_forwarded(self):
        """Only kwargs matching declared parameters are forwarded."""
        received = {}

        class SelectiveHook(Hook):
            def call(self, recipe_path: Path, context: dict[str, Any], recipe=None):
                received["recipe"] = recipe
                return None

        hook = SelectiveHook()
        path = Path("/tmp/test")
        ctx = {"a": 1}
        # 'other' should be silently dropped since call() doesn't declare it
        result_path, result_ctx = hook(path, ctx, recipe="the_recipe", other="dropped")

        self.assertEqual(result_path, path)
        self.assertEqual(result_ctx, ctx)
        self.assertEqual(received["recipe"], "the_recipe")

    def test_no_kwargs_passed_when_none_provided(self):
        """Hook works normally when called without any extra kwargs."""

        class BasicHook(Hook):
            def call(self, recipe_path: Path, context: dict[str, Any], **kwargs):
                return (recipe_path, {**context, "kwargs_count": len(kwargs)})

        hook = BasicHook()
        path = Path("/tmp/test")
        ctx = {"x": 1}
        result_path, result_ctx = hook(path, ctx)

        self.assertEqual(result_ctx["kwargs_count"], 0)

    def test_hook_return_none_preserves_original_values(self):
        """When call() returns None, original path and context are returned."""

        class NoOpHook(Hook):
            def call(self, recipe_path: Path, context: dict[str, Any], **kwargs):
                return None

        hook = NoOpHook()
        path = Path("/tmp/original")
        ctx = {"original": True}
        result_path, result_ctx = hook(path, ctx, recipe="something")

        self.assertEqual(result_path, path)
        self.assertEqual(result_ctx, ctx)

    def test_hook_can_modify_path(self):
        """Hook can return a modified path."""

        class PathModifyingHook(Hook):
            def call(self, recipe_path: Path, context: dict[str, Any], **kwargs):
                return (recipe_path / "subdir", context)

        hook = PathModifyingHook()
        path = Path("/tmp/test")
        ctx = {"key": "value"}
        result_path, result_ctx = hook(path, ctx)

        self.assertEqual(result_path, Path("/tmp/test/subdir"))
        self.assertEqual(result_ctx, ctx)

    def test_hook_can_modify_context(self):
        """Hook can return a modified context."""

        class ContextModifyingHook(Hook):
            def call(self, recipe_path: Path, context: dict[str, Any], **kwargs):
                new_ctx = {**context, "injected": True}
                return (recipe_path, new_ctx)

        hook = ContextModifyingHook()
        path = Path("/tmp/test")
        ctx = {"original": True}
        result_path, result_ctx = hook(path, ctx)

        self.assertEqual(result_ctx, {"original": True, "injected": True})

    def test_hook_with_recipe_kwarg_can_mutate_recipe(self):
        """A hook receiving recipe kwarg can interact with the recipe instance."""
        mutations = []

        class MutatingHook(Hook):
            def call(self, recipe_path: Path, context: dict[str, Any], recipe=None):
                if recipe is not None:
                    mutations.append(recipe)
                return None

        hook = MutatingHook()
        mock_recipe = object()
        hook(Path("/tmp"), {}, recipe=mock_recipe)

        self.assertEqual(len(mutations), 1)
        self.assertIs(mutations[0], mock_recipe)

    def test_backwards_compat_old_style_hook(self):
        """Old-style hooks with only (recipe_path, context) still work."""

        class OldStyleHook(Hook):
            def call(self, recipe_path, context):
                return (recipe_path, {**context, "old_style": True})

        hook = OldStyleHook()
        result_path, result_ctx = hook(Path("/tmp"), {"a": 1}, recipe="ignored")

        self.assertEqual(result_ctx, {"a": 1, "old_style": True})

    def test_hook_is_pydantic_model(self):
        """Hook subclasses are valid Pydantic models with configurable fields."""

        class ConfigurableHook(Hook):
            multiplier: int = 2

            def call(self, recipe_path: Path, context: dict[str, Any], **kwargs):
                return (recipe_path, {**context, "multiplied": self.multiplier * 3})

        hook = ConfigurableHook(multiplier=5)
        _, result_ctx = hook(Path("/tmp"), {})

        self.assertEqual(result_ctx["multiplied"], 15)

    def test_hook_with_optional_return_type(self):
        """Hook call() with Optional return type annotation works."""

        class TypedHook(Hook):
            def call(self, recipe_path: Path, context: dict[str, Any], **kwargs) -> Optional[tuple[Path, dict]]:
                if context.get("skip"):
                    return None
                return (recipe_path, {**context, "processed": True})

        hook = TypedHook()

        # When returning None
        path, ctx = hook(Path("/tmp"), {"skip": True})
        self.assertNotIn("processed", ctx)

        # When returning a tuple
        path, ctx = hook(Path("/tmp"), {"skip": False})
        self.assertTrue(ctx["processed"])


if __name__ == "__main__":
    unittest.main()
