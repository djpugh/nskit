"""Unit tests for DerivedFieldEvaluator."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from nskit.client.context import ContextProvider
from nskit.client.derived_evaluator import DerivedFieldEvaluator


class TestDerivedFieldEvaluator(unittest.TestCase):
    """Tests for DerivedFieldEvaluator template evaluation."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.evaluator = DerivedFieldEvaluator()

    def test_simple_substitution(self) -> None:
        """Evaluates a simple variable substitution."""
        result = self.evaluator.evaluate("{{ project_name }}", {"project_name": "my-app"})
        self.assertEqual(result, "my-app")

    def test_slugify_filter(self) -> None:
        """Applies the slugify filter."""
        result = self.evaluator.evaluate("{{ name | slugify }}", {"name": "My Cool Project"})
        self.assertEqual(result, "my-cool-project")

    def test_snake_case_filter(self) -> None:
        """Applies the snake_case filter."""
        result = self.evaluator.evaluate("{{ name | snake_case }}", {"name": "My Cool Project"})
        self.assertEqual(result, "my_cool_project")

    def test_camel_case_filter(self) -> None:
        """Applies the camel_case filter."""
        result = self.evaluator.evaluate("{{ name | camel_case }}", {"name": "my cool project"})
        self.assertEqual(result, "MyCoolProject")

    def test_upper_filter(self) -> None:
        """Applies the upper filter."""
        result = self.evaluator.evaluate("{{ name | upper }}", {"name": "hello"})
        self.assertEqual(result, "HELLO")

    def test_context_provider_values(self) -> None:
        """Context provider values are available under ctx namespace."""
        mock_provider = MagicMock(spec=ContextProvider)
        mock_provider.get_context.return_value = {"username": "testuser"}
        evaluator = DerivedFieldEvaluator(context_provider=mock_provider)
        result = evaluator.evaluate("{{ ctx.username }}", {})
        self.assertEqual(result, "testuser")

    def test_no_context_provider(self) -> None:
        """Works without a context provider (ctx not available)."""
        result = self.evaluator.evaluate("{{ name }}", {"name": "hello"})
        self.assertEqual(result, "hello")


if __name__ == "__main__":
    unittest.main()
