"""Field specification models for interactive recipe initialisation."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


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
        operator: Comparison operator (equals, not_equals, in, not_in).
        value: Value to compare against.
        action: Action to take when the condition is met.
    """

    depends_on: str
    operator: str
    value: Any
    action: ConditionalAction


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
