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


class TestHiddenFields(unittest.TestCase):
    """Hidden fields are resolved but never prompted for.

    ``FieldSpec.hidden`` marks a value the recipe pins or derives. The parser
    setting the flag is not enough — the handler has to honour it, or the flag is
    inert and the user is still asked.
    """

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.handler = InteractiveHandler()

    def test_hidden_field_is_not_prompted(self) -> None:
        """No prompt is issued for a hidden field."""
        fields = InputFieldsResponse(fields=[FieldSpec(name="pinned", default=True, hidden=True)])
        with patch.object(self.handler, "_prompt_field") as prompt:
            self.handler.collect_field_values(fields)
            prompt.assert_not_called()

    def test_hidden_field_default_is_kept(self) -> None:
        """A hidden field's resolved default is still collected.

        Dropping it would mean a pinned or derived value never materialises.
        """
        fields = InputFieldsResponse(fields=[FieldSpec(name="pinned", default=True, hidden=True)])
        with patch.object(self.handler, "_prompt_field"):
            collected = self.handler.collect_field_values(fields)
        self.assertEqual(collected, {"pinned": True})

    def test_hidden_field_without_default_is_omitted(self) -> None:
        """A hidden field with nothing to resolve contributes no value."""
        fields = InputFieldsResponse(fields=[FieldSpec(name="pinned", hidden=True)])
        with patch.object(self.handler, "_prompt_field"):
            collected = self.handler.collect_field_values(fields)
        self.assertEqual(collected, {})

    def test_hidden_required_field_does_not_cancel(self) -> None:
        """A hidden required field must not abort collection.

        The unprompted path returns no value, and a required field with no value
        normally cancels; hidden fields have to bypass that.
        """
        fields = InputFieldsResponse(fields=[FieldSpec(name="pinned", default=True, required=True, hidden=True)])
        with patch.object(self.handler, "_prompt_field"):
            self.assertIsNotNone(self.handler.collect_field_values(fields))

    def test_visible_fields_are_still_prompted(self) -> None:
        """Hiding one field does not suppress the others."""
        fields = InputFieldsResponse(
            fields=[
                FieldSpec(name="pinned", default=True, hidden=True),
                FieldSpec(name="asked", default="x"),
            ]
        )
        with patch.object(self.handler, "_prompt_field", return_value="answer") as prompt:
            collected = self.handler.collect_field_values(fields)
        self.assertEqual(prompt.call_count, 1)
        self.assertEqual(collected, {"pinned": True, "asked": "answer"})

    def test_pre_filled_value_wins_over_hidden_default(self) -> None:
        """An explicitly supplied value is not overwritten by the pinned default."""
        fields = InputFieldsResponse(fields=[FieldSpec(name="pinned", default=True, hidden=True)])
        collected = self.handler.collect_field_values(fields, pre_filled={"pinned": "supplied"})
        self.assertEqual(collected, {"pinned": "supplied"})


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


class TestOptionsProvider(unittest.TestCase):
    """Tests for InteractiveHandler options_provider resolution."""

    def test_options_provider_populates_options(self) -> None:
        """A registered options_provider callable populates field.options at prompt time."""
        handler = InteractiveHandler(
            options_providers={"domains": lambda field, default: ["alpha", "beta"]},
        )
        field = FieldSpec(name="domain", options_provider="domains")
        handler._prompt_choice_field = MagicMock(return_value="alpha")
        handler._prompt_field(field, None)
        self.assertEqual(field.options, ["alpha", "beta"])
        handler._prompt_choice_field.assert_called_once_with(field, None)

    def test_options_provider_promotes_type_to_enum(self) -> None:
        """Field type is promoted to ENUM when options are resolved dynamically."""
        handler = InteractiveHandler(
            options_providers={"regions": lambda field, default: ["eu-west-1", "us-east-1"]},
        )
        field = FieldSpec(name="region", type=FieldType.STR, options_provider="regions")
        handler._prompt_choice_field = MagicMock(return_value="eu-west-1")
        handler._prompt_field(field, None)
        self.assertEqual(field.type, FieldType.ENUM)

    def test_options_provider_unregistered_name_is_ignored(self) -> None:
        """An unregistered provider name does not crash; field stays as-is."""
        handler = InteractiveHandler(options_providers={})
        field = FieldSpec(name="x", options_provider="missing")
        handler._prompt_str_field = MagicMock(return_value="typed")
        result = handler._prompt_field(field, None)
        self.assertEqual(result, "typed")
        self.assertIsNone(field.options)

    def test_options_provider_no_arg_fallback(self) -> None:
        """Provider that does not accept args is called with no args."""

        def no_arg_provider():
            return ["one", "two"]

        handler = InteractiveHandler(options_providers={"noarg": no_arg_provider})
        field = FieldSpec(name="x", options_provider="noarg")
        handler._prompt_choice_field = MagicMock(return_value="one")
        handler._prompt_field(field, None)
        self.assertEqual(field.options, ["one", "two"])

    def test_options_provider_exception_is_swallowed(self) -> None:
        """Provider that raises does not crash the handler."""

        def bad_provider():
            raise RuntimeError("boom")

        handler = InteractiveHandler(options_providers={"bad": bad_provider})
        field = FieldSpec(name="x", options_provider="bad")
        handler._prompt_str_field = MagicMock(return_value="fallback")
        result = handler._prompt_field(field, "fallback")
        self.assertEqual(result, "fallback")
        self.assertIsNone(field.options)

    def test_options_provider_receives_field_and_default(self) -> None:
        """Provider receiving (field, default) gets the correct arguments."""
        received = {}

        def capturing_provider(field, default):
            received["field_name"] = field.name
            received["default"] = default
            return ["opt1"]

        handler = InteractiveHandler(options_providers={"cap": capturing_provider})
        field = FieldSpec(name="my_field", options_provider="cap")
        handler._prompt_choice_field = MagicMock(return_value="opt1")
        handler._prompt_field(field, "my_default")
        self.assertEqual(received["field_name"], "my_field")
        self.assertEqual(received["default"], "my_default")

    def test_options_provider_empty_list_does_not_promote(self) -> None:
        """An empty options list from provider does not promote the field type."""
        handler = InteractiveHandler(
            options_providers={"empty": lambda field, default: []},
        )
        field = FieldSpec(name="x", type=FieldType.STR, options_provider="empty")
        handler._prompt_str_field = MagicMock(return_value="typed")
        handler._prompt_field(field, None)
        self.assertEqual(field.type, FieldType.STR)


class TestDefaultProvider(unittest.TestCase):
    """Tests for InteractiveHandler default_provider resolution."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.handler = InteractiveHandler(
            default_providers={"account_id": lambda collected: "123456789012"},
        )

    def test_default_provider_returns_value(self) -> None:
        """default_provider value is used when env_var and template are absent."""
        field = FieldSpec(name="account", default_provider="account_id")
        result = self.handler._resolve_default(field, {})
        self.assertEqual(result, "123456789012")

    def test_default_provider_receives_collected_values(self) -> None:
        """Provider callable receives previously collected values."""
        received = {}

        def provider(collected):
            received.update(collected)
            return "resolved"

        handler = InteractiveHandler(default_providers={"ctx": provider})
        field = FieldSpec(name="x", default_provider="ctx")
        handler._resolve_default(field, {"domain": "alpha", "region": "eu-west-1"})
        self.assertEqual(received, {"domain": "alpha", "region": "eu-west-1"})

    def test_default_provider_none_result_falls_through(self) -> None:
        """Provider returning None falls through to static default."""
        handler = InteractiveHandler(
            default_providers={"nope": lambda collected: None},
        )
        field = FieldSpec(name="x", default="static", default_provider="nope")
        result = handler._resolve_default(field, {})
        self.assertEqual(result, "static")

    def test_default_provider_exception_falls_through(self) -> None:
        """Provider that raises falls through to static default."""
        handler = InteractiveHandler(
            default_providers={"boom": lambda collected: 1 / 0},
        )
        field = FieldSpec(name="x", default="safe", default_provider="boom")
        result = handler._resolve_default(field, {})
        self.assertEqual(result, "safe")

    def test_default_provider_unregistered_name_falls_through(self) -> None:
        """An unregistered provider name falls through to static default."""
        handler = InteractiveHandler(default_providers={})
        field = FieldSpec(name="x", default="static", default_provider="missing")
        result = handler._resolve_default(field, {})
        self.assertEqual(result, "static")

    def test_default_provider_used_for_hidden_field(self) -> None:
        """A hidden field still resolves via default_provider."""
        handler = InteractiveHandler(
            default_providers={"auto": lambda collected: "auto_val"},
        )
        fields = InputFieldsResponse(fields=[FieldSpec(name="x", hidden=True, default_provider="auto")])
        with patch.object(handler, "_prompt_field") as prompt:
            collected = handler.collect_field_values(fields)
        prompt.assert_not_called()
        self.assertEqual(collected, {"x": "auto_val"})


class TestProviderIntegration(unittest.TestCase):
    """Integration tests for the full collect_field_values flow with providers.

    These test the real end-to-end behaviour: field ordering, dispatch to the
    correct prompt method, cross-field dependency via collected values, and
    edge-case return values.
    """

    def test_options_provider_routes_to_choice_prompt(self) -> None:
        """A field with options_provider dispatches to _prompt_choice_field in full flow."""
        handler = InteractiveHandler(
            options_providers={"colours": lambda field, default: ["red", "green", "blue"]},
        )
        fields = InputFieldsResponse(fields=[FieldSpec(name="colour", options_provider="colours")])
        with (
            patch.object(handler, "_prompt_choice_field", return_value="green") as choice,
            patch.object(handler, "_prompt_str_field") as str_prompt,
        ):
            result = handler.collect_field_values(fields)
        choice.assert_called_once()
        str_prompt.assert_not_called()
        self.assertEqual(result, {"colour": "green"})

    def test_default_provider_sees_earlier_field_values(self) -> None:
        """default_provider for field B receives field A's collected value."""
        received_values = {}

        def account_provider(collected):
            received_values.update(collected)
            return f"account-for-{collected.get('domain', 'unknown')}"

        handler = InteractiveHandler(
            options_providers={"domains": lambda: ["analytics", "genomics"]},
            default_providers={"resolve_account": account_provider},
        )
        fields = InputFieldsResponse(
            fields=[
                FieldSpec(name="domain", options_provider="domains"),
                FieldSpec(name="account_id", default_provider="resolve_account"),
            ]
        )
        # Simulate user picking "genomics" for domain, accepting default for account_id
        with (
            patch.object(handler, "_prompt_choice_field", return_value="genomics"),
            patch.object(handler, "_prompt_str_field", side_effect=lambda f, d: d),
        ):
            result = handler.collect_field_values(fields)

        self.assertEqual(result["domain"], "genomics")
        self.assertEqual(result["account_id"], "account-for-genomics")
        self.assertIn("domain", received_values)
        self.assertEqual(received_values["domain"], "genomics")

    def test_full_flow_with_multiple_dependent_providers(self) -> None:
        """Multiple fields chaining: options → default → default."""
        handler = InteractiveHandler(
            options_providers={
                "regions": lambda: ["eu-west-1", "us-east-1"],
            },
            default_providers={
                "region_vpc": lambda cv: f"vpc-{cv.get('region', 'none')}",
                "region_subnet": lambda cv: f"{cv.get('vpc', 'none')}-subnet-a",
            },
        )
        fields = InputFieldsResponse(
            fields=[
                FieldSpec(name="region", options_provider="regions"),
                FieldSpec(name="vpc", default_provider="region_vpc"),
                FieldSpec(name="subnet", default_provider="region_subnet"),
            ]
        )
        # User picks region, accepts all defaults
        with (
            patch.object(handler, "_prompt_choice_field", return_value="eu-west-1"),
            patch.object(handler, "_prompt_str_field", side_effect=lambda f, d: d),
        ):
            result = handler.collect_field_values(fields)

        self.assertEqual(result["region"], "eu-west-1")
        self.assertEqual(result["vpc"], "vpc-eu-west-1")
        self.assertEqual(result["subnet"], "vpc-eu-west-1-subnet-a")

    def test_default_provider_falsy_zero_is_kept(self) -> None:
        """Provider returning 0 is kept (not treated as missing)."""
        handler = InteractiveHandler(
            default_providers={"zero": lambda cv: 0},
        )
        field = FieldSpec(name="x", default="fallback", default_provider="zero")
        result = handler._resolve_default(field, {})
        self.assertEqual(result, 0)

    def test_default_provider_falsy_false_is_kept(self) -> None:
        """Provider returning False is kept (not treated as missing)."""
        handler = InteractiveHandler(
            default_providers={"no": lambda cv: False},
        )
        field = FieldSpec(name="x", default="fallback", default_provider="no")
        result = handler._resolve_default(field, {})
        self.assertIs(result, False)

    def test_default_provider_empty_string_is_kept(self) -> None:
        """Provider returning empty string is kept (not treated as missing)."""
        handler = InteractiveHandler(
            default_providers={"blank": lambda cv: ""},
        )
        field = FieldSpec(name="x", default="fallback", default_provider="blank")
        result = handler._resolve_default(field, {})
        self.assertEqual(result, "")

    def test_default_provider_with_hidden_dependent_chain(self) -> None:
        """Hidden field resolved by provider feeds into next hidden field's provider."""
        handler = InteractiveHandler(
            default_providers={
                "step1": lambda cv: "intermediate",
                "step2": lambda cv: f"{cv.get('a', '?')}-final",
            },
        )
        fields = InputFieldsResponse(
            fields=[
                FieldSpec(name="a", hidden=True, default_provider="step1"),
                FieldSpec(name="b", hidden=True, default_provider="step2"),
            ]
        )
        result = handler.collect_field_values(fields)
        self.assertEqual(result, {"a": "intermediate", "b": "intermediate-final"})

    def test_options_provider_failure_still_collects_value(self) -> None:
        """When options_provider fails, field falls back to str prompt and still collects."""

        def failing_provider():
            raise ConnectionError("API unavailable")

        handler = InteractiveHandler(options_providers={"broken": failing_provider})
        fields = InputFieldsResponse(fields=[FieldSpec(name="x", options_provider="broken")])
        with patch.object(handler, "_prompt_str_field", return_value="manually-typed"):
            result = handler.collect_field_values(fields)
        self.assertEqual(result, {"x": "manually-typed"})


if __name__ == "__main__":
    unittest.main()
