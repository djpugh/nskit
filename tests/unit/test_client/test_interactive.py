"""Unit tests for InteractiveHandler."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from nskit.client.field_models import (
    ConditionalAction,
    ConditionalRule,
    FieldSpec,
    FieldType,
    InputFieldsResponse,
)
from nskit.client.interactive import InteractiveHandler


class TestResolveDefault(unittest.TestCase):
    """Tests for InteractiveHandler._resolve_default."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.handler = InteractiveHandler()

    def test_env_var_takes_priority(self) -> None:
        """Environment variable value is returned when set."""
        self.handler.env_resolver = MagicMock()
        self.handler.env_resolver.resolve.return_value = "from_env"
        field = FieldSpec(name="x", env_var="NSKIT_X", default="static")
        result = self.handler._resolve_default(field, {})
        self.assertEqual(result, "from_env")

    def test_template_fallback(self) -> None:
        """Template is evaluated when env var returns None."""
        self.handler.env_resolver = MagicMock()
        self.handler.env_resolver.resolve.return_value = None
        self.handler.derived_evaluator = MagicMock()
        self.handler.derived_evaluator.evaluate.return_value = "from_template"
        field = FieldSpec(name="x", env_var="NSKIT_X", template="{{ name }}-svc")
        result = self.handler._resolve_default(field, {"name": "foo"})
        self.assertEqual(result, "from_template")

    def test_static_default_fallback(self) -> None:
        """Static default is returned when env and template are absent."""
        field = FieldSpec(name="x", default="fallback")
        result = self.handler._resolve_default(field, {})
        self.assertEqual(result, "fallback")

    def test_template_exception_falls_through(self) -> None:
        """Template evaluation error falls back to static default."""
        self.handler.env_resolver = MagicMock()
        self.handler.env_resolver.resolve.return_value = None
        self.handler.derived_evaluator = MagicMock()
        self.handler.derived_evaluator.evaluate.side_effect = RuntimeError("bad")
        field = FieldSpec(name="x", template="{{ bad }}", default="safe")
        result = self.handler._resolve_default(field, {})
        self.assertEqual(result, "safe")

    def test_no_env_var_skips_resolver(self) -> None:
        """When env_var is None, resolver is not called."""
        self.handler.env_resolver = MagicMock()
        field = FieldSpec(name="x", default="val")
        self.handler._resolve_default(field, {})
        self.handler.env_resolver.resolve.assert_not_called()

    def test_template_empty_result_falls_through(self) -> None:
        """Empty template result falls back to static default."""
        self.handler.env_resolver = MagicMock()
        self.handler.env_resolver.resolve.return_value = None
        self.handler.derived_evaluator = MagicMock()
        self.handler.derived_evaluator.evaluate.return_value = ""
        field = FieldSpec(name="x", template="{{ x }}", default="static")
        result = self.handler._resolve_default(field, {})
        self.assertEqual(result, "static")


class TestShouldShowField(unittest.TestCase):
    """Tests for InteractiveHandler._should_show_field."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.handler = InteractiveHandler()

    def test_no_rules_shows_field(self) -> None:
        """Field with no conditional rules is always shown."""
        field = FieldSpec(name="x")
        self.assertTrue(self.handler._should_show_field(field, {}))

    def test_skip_on_equals(self) -> None:
        """Field is hidden when skip rule matches."""
        rule = ConditionalRule(depends_on="use_docker", operator="equals", value=False, action=ConditionalAction.SKIP)
        field = FieldSpec(name="docker_image", conditional_rules=[rule])
        self.assertFalse(self.handler._should_show_field(field, {"use_docker": False}))

    def test_show_when_condition_not_met(self) -> None:
        """Field is shown when skip condition is not met."""
        rule = ConditionalRule(depends_on="use_docker", operator="equals", value=False, action=ConditionalAction.SKIP)
        field = FieldSpec(name="docker_image", conditional_rules=[rule])
        self.assertTrue(self.handler._should_show_field(field, {"use_docker": True}))

    def test_missing_dependency_is_ignored(self) -> None:
        """Rule is skipped when depends_on field not yet collected."""
        rule = ConditionalRule(depends_on="missing", operator="equals", value="x", action=ConditionalAction.SKIP)
        field = FieldSpec(name="y", conditional_rules=[rule])
        self.assertTrue(self.handler._should_show_field(field, {}))

    def test_not_equals_operator(self) -> None:
        """not_equals operator works correctly."""
        rule = ConditionalRule(depends_on="lang", operator="not_equals", value="python", action=ConditionalAction.SKIP)
        field = FieldSpec(name="py_version", conditional_rules=[rule])
        # lang is "go" != "python" → condition met → skip
        self.assertFalse(self.handler._should_show_field(field, {"lang": "go"}))

    def test_in_operator(self) -> None:
        """in operator matches value in list."""
        rule = ConditionalRule(
            depends_on="lang", operator="in", value=["python", "ruby"], action=ConditionalAction.SKIP
        )
        field = FieldSpec(name="x", conditional_rules=[rule])
        self.assertFalse(self.handler._should_show_field(field, {"lang": "python"}))

    def test_not_in_operator(self) -> None:
        """not_in operator skips when value is absent from list."""
        rule = ConditionalRule(
            depends_on="lang", operator="not_in", value=["python", "ruby"], action=ConditionalAction.SKIP
        )
        field = FieldSpec(name="x", conditional_rules=[rule])
        self.assertFalse(self.handler._should_show_field(field, {"lang": "go"}))

    def test_unknown_operator_does_not_skip(self) -> None:
        """Unknown operator evaluates to False, field is shown."""
        rule = ConditionalRule(depends_on="a", operator="greater_than", value=5, action=ConditionalAction.SKIP)
        field = FieldSpec(name="x", conditional_rules=[rule])
        self.assertTrue(self.handler._should_show_field(field, {"a": 10}))


class TestCollectFieldValues(unittest.TestCase):
    """Tests for InteractiveHandler.collect_field_values."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.handler = InteractiveHandler()

    def test_pre_filled_values_skip_prompt(self) -> None:
        """Pre-filled values are used without prompting."""
        fields = InputFieldsResponse(fields=[FieldSpec(name="x", default="d")])
        result = self.handler.collect_field_values(fields, pre_filled={"x": "given"})
        self.assertEqual(result, {"x": "given"})

    def test_skipped_field_not_in_result(self) -> None:
        """Conditionally skipped fields are excluded."""
        rule = ConditionalRule(depends_on="a", operator="equals", value="skip", action=ConditionalAction.SKIP)
        fields = InputFieldsResponse(
            fields=[
                FieldSpec(name="a", default="skip"),
                FieldSpec(name="b", conditional_rules=[rule], default="val"),
            ]
        )
        result = self.handler.collect_field_values(fields)
        self.assertNotIn("b", result)

    def test_required_field_none_returns_none(self) -> None:
        """Returns None when a required field gets no value."""
        handler = InteractiveHandler()
        handler._prompt_field = MagicMock(return_value=None)
        fields = InputFieldsResponse(fields=[FieldSpec(name="x", required=True)])
        result = handler.collect_field_values(fields)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
