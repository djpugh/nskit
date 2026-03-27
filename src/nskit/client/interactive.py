"""Interactive handler for recipe field collection."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from nskit.client.derived_evaluator import DerivedFieldEvaluator
from nskit.client.env_resolver import EnvVarResolver
from nskit.client.field_models import ConditionalAction, FieldSpec, FieldType, InputFieldsResponse
from nskit.client.field_parser import FieldParser
from nskit.client.models import RecipeInfo


class InteractiveHandler:
    """Handles interactive field collection for recipe initialisation.

    Uses dependency injection for the actual prompt library so the client
    layer stays free of CLI dependencies. Subclass and override the
    ``_prompt_*`` methods to plug in a different prompt library.

    Args:
        field_parser: Parser for field specifications.
        env_resolver: Resolver for environment variable defaults.
        derived_evaluator: Evaluator for template-based defaults.
    """

    def __init__(
        self,
        field_parser: FieldParser | None = None,
        env_resolver: EnvVarResolver | None = None,
        derived_evaluator: DerivedFieldEvaluator | None = None,
    ) -> None:
        self.field_parser = field_parser or FieldParser()
        self.env_resolver = env_resolver or EnvVarResolver()
        self.derived_evaluator = derived_evaluator or DerivedFieldEvaluator()

    def select_recipe(self, recipes: list[RecipeInfo]) -> RecipeInfo | None:
        """Present recipe selection to the user.

        Args:
            recipes: Available recipes.

        Returns:
            Selected recipe, or ``None`` if cancelled.
        """
        if not recipes:
            return None
        if len(recipes) == 1:
            return recipes[0]
        # Default implementation returns first recipe.
        # CLI layer overrides with actual prompt.
        return recipes[0]

    def collect_field_values(
        self,
        fields: InputFieldsResponse,
        pre_filled: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Collect values for all fields interactively.

        Iterates through fields, skipping pre-filled ones and evaluating
        conditional rules. Resolves defaults via the env_var → template →
        static chain.

        Args:
            fields: Field specifications to collect.
            pre_filled: Values already provided (will not be prompted).

        Returns:
            Collected values dictionary, or ``None`` if cancelled.
        """
        pre_filled = pre_filled or {}
        collected: dict[str, Any] = {}

        for field in fields.fields:
            # Use pre-filled value if available
            if field.name in pre_filled:
                collected[field.name] = pre_filled[field.name]
                continue

            # Evaluate conditional rules
            if not self._should_show_field(field, collected):
                continue

            # Resolve default value
            default = self._resolve_default(field, collected)

            # Prompt for value
            try:
                value = self._prompt_field(field, default)
            except KeyboardInterrupt:
                return None

            if value is not None:
                collected[field.name] = value
            elif field.required:
                return None

        return collected

    def confirm_initialisation(
        self,
        recipe_name: str,
        output_dir: Path,
        values: dict[str, Any],
    ) -> bool:
        """Display summary and prompt for confirmation.

        Args:
            recipe_name: Name of the recipe.
            output_dir: Target output directory.
            values: Collected field values.

        Returns:
            ``True`` if the user confirms, ``False`` otherwise.
        """
        # Default implementation always confirms.
        # CLI layer overrides with actual prompt.
        return True

    def _resolve_default(self, field: FieldSpec, collected_values: dict[str, Any]) -> Any:
        """Resolve field default: env_var → template → static default.

        Args:
            field: Field specification.
            collected_values: Previously collected values.

        Returns:
            Resolved default value, or ``None``.
        """
        # 1. Try environment variable
        if field.env_var:
            env_value = self.env_resolver.resolve(field.env_var)
            if env_value is not None:
                return env_value

        # 2. Try template expression
        if field.template:
            try:
                result = self.derived_evaluator.evaluate(field.template, collected_values)
                if result:
                    return result
            except Exception:  # nosec B110
                pass

        # 3. Fall back to static default
        return field.default

    def _should_show_field(self, field: FieldSpec, collected_values: dict[str, Any]) -> bool:
        """Evaluate conditional rules to determine field visibility."""
        for rule in field.conditional_rules:
            if rule.depends_on not in collected_values:
                continue
            dep_value = collected_values[rule.depends_on]
            condition_met = self._evaluate_condition(dep_value, rule.operator, rule.value)
            if condition_met and rule.action == ConditionalAction.SKIP:
                return False
        return True

    def _evaluate_condition(self, actual: Any, operator: str, expected: Any) -> bool:
        """Evaluate a single conditional expression."""
        if operator == "equals":
            return actual == expected
        if operator == "not_equals":
            return actual != expected
        if operator == "in":
            return actual in expected
        if operator == "not_in":
            return actual not in expected
        return False

    def _prompt_field(self, field: FieldSpec, default: Any) -> Any:
        """Dispatch to the appropriate prompt method for the field type.

        Args:
            field: Field specification.
            default: Resolved default value.

        Returns:
            User-provided value.
        """
        dispatch = {
            FieldType.BOOL: self._prompt_bool_field,
            FieldType.INT: self._prompt_int_field,
            FieldType.FLOAT: self._prompt_float_field,
            FieldType.ENUM: self._prompt_choice_field,
        }
        handler = dispatch.get(field.type, self._prompt_str_field)
        return handler(field, default)

    def _prompt_str_field(self, field: FieldSpec, default: Any) -> Any:
        """Prompt for a string value. Override in CLI subclass."""
        return default

    def _prompt_bool_field(self, field: FieldSpec, default: Any) -> Any:
        """Prompt for a boolean value. Override in CLI subclass."""
        return default

    def _prompt_int_field(self, field: FieldSpec, default: Any) -> Any:
        """Prompt for an integer value. Override in CLI subclass."""
        return default

    def _prompt_float_field(self, field: FieldSpec, default: Any) -> Any:
        """Prompt for a float value. Override in CLI subclass."""
        return default

    def _prompt_choice_field(self, field: FieldSpec, default: Any) -> Any:
        """Prompt for a choice from options. Override in CLI subclass."""
        return default
