"""Field specification models for interactive recipe initialisation."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

# Short operator aliases accepted in the ``"op:value"`` condition string form,
# mapped to the canonical operators used by the interactive evaluator.
_OPERATOR_ALIASES = {
    "eq": "equals",
    "ne": "not_equals",
    "equals": "equals",
    "not_equals": "not_equals",
    "in": "in",
    "not_in": "not_in",
    "gt": "gt",
    "lt": "lt",
}


class FieldType(str, Enum):
    """Supported field types for recipe parameters."""

    STR = "str"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    ENUM = "enum"
    LIST = "list"
    DICT = "dict"
    OBJECT = "object"


class ConditionalAction(str, Enum):
    """Actions to take when a conditional rule is satisfied."""

    SKIP = "skip"


class ConditionalRule(BaseModel):
    """Rule that controls field visibility based on another field's value.

    Args:
        depends_on: Name of the field this rule depends on.
        operator: Comparison operator (equals, not_equals, in, not_in, gt, lt).
        value: Value to compare against.
        action: Action to take when the condition is met.
        condition: Optional shorthand ``"op:value"`` form (e.g. ``"ne:true"``,
            ``"in:a,b"``). When given, ``operator`` and ``value`` are derived
            from it. Provided for compatibility with string-based condition
            formats; ``operator``/``value`` are the canonical fields.
    """

    depends_on: str
    operator: str = "equals"
    value: Any = None
    action: ConditionalAction = ConditionalAction.SKIP

    @model_validator(mode="before")
    @classmethod
    def _expand_condition_string(cls, data: Any) -> Any:
        """Derive operator/value from a ``"op:value"`` ``condition`` shorthand."""
        if not isinstance(data, dict) or "condition" not in data:
            return data
        data = dict(data)
        condition = data.pop("condition")
        if isinstance(condition, str):
            raw_op, _, raw_value = condition.partition(":")
            operator = _OPERATOR_ALIASES.get(raw_op.strip().lower(), raw_op.strip().lower())
            data.setdefault("operator", operator)
            if "value" not in data:
                if operator in ("in", "not_in"):
                    data["value"] = [v.strip() for v in raw_value.split(",")] if raw_value else []
                else:
                    data["value"] = raw_value.strip()
        return data


class FieldSpec(BaseModel):
    """Specification for a single recipe field.

    Args:
        name: Field identifier.
        type: Data type of the field.
        required: Whether the field must be provided.
        default: Default value for the field.
        display_name: Human-readable name for display.
        prompt_text: Custom prompt text for interactive collection.
        description: Description of the field's purpose.
        help_text: Additional help text shown alongside the prompt.
        options: Available choices for enum-type fields.
        env_var: Environment variable name for default resolution.
        template: Jinja2 template expression for derived defaults.
        conditional_rules: Rules controlling field visibility.
    """

    name: str
    type: FieldType = FieldType.STR
    required: bool = True
    default: Any = None
    display_name: str | None = None
    prompt_text: str | None = None
    description: str | None = None
    help_text: str | None = None
    options: list[str] | None = None
    env_var: str | None = None
    template: str | None = None
    conditional_rules: list[ConditionalRule] = Field(default_factory=list)


class InputFieldsResponse(BaseModel):
    """Response containing field specifications and metadata.

    Args:
        fields: List of field specifications.
        metadata: Additional metadata about the fields.
    """

    fields: list[FieldSpec] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
